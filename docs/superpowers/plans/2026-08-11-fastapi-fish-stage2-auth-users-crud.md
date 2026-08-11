# FastAPI-Fish Stage 2: Auth Flow & Users CRUD — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring FastAPI-Fish's auth flow and Users API to full contract parity with KotlinFish: JWT access/refresh tokens with rotation and server-side revocation, `register`/`login`/`refresh`/`logout` endpoints, and a Users CRUD API with pagination, filters, RBAC, and ownership rules.

**Architecture:** This is Plan 2 of 4 bringing FastAPI-Fish to parity with KotlinFish (see `docs/superpowers/specs/2026-08-08-fastapi-fish-parity-design.md`). Plan 1 (merged) fixed boot and replaced the data layer (SQLAlchemy models, Alembic migration, `UnitOfWork.user_repo`/`refresh_token_repo`). **This plan** = spec stages 3+4 (auth flow, users CRUD contract). Plan 3 = spec stages 5+6 (unified error codes/`X-Trace-Id`, observability, admin bootstrap-on-startup). Plan 4 = spec stages 7+8 (templating, Postgres-backed test suite, CI).

**Tech Stack:** FastAPI, SQLAlchemy 2.0 (async), PyJWT, passlib (argon2), Pydantic v2, Dynaconf, pytest + pytest-asyncio, httpx/`TestClient`, aiosqlite (test-only).

## Global Constraints

- Builds on Plan 1's data layer (`app.infrastructure.models.User`/`RefreshToken`, `UnitOfWork.user_repo`/`refresh_token_repo`) — already merged to `main`. This plan does not modify the DB schema or migration.
- Every task must leave `python -c "import app.main"` (run from `src/`) succeeding, and `cd src && python -m pytest tests/ -v` fully green — no task may end with a broken import chain or a regressed previously-green test. Where a task intentionally leaves an existing runtime call-path broken pending a later task in *this same plan* (there is exactly one such case, called out in Task 2), it is because no currently-passing test exercises that path — this mirrors Plan 1's own precedent of flagging such gaps explicitly rather than pretending they don't exist.
- Tests run from repo root as `cd src && python -m pytest tests/<file>.py -v` (or `tests/` for the whole suite). `pytest.ini` already exists from Plan 1.
- All tests in this plan run against SQLite (`aiosqlite`, in-memory, `StaticPool`) — no Docker/Postgres required. A comprehensive Postgres-backed integration suite is explicitly deferred to Plan 4 (spec stage 8), matching how Plan 1 only required live Postgres for its one Alembic-verification task.
- **Out of scope (deferred to Plan 3, spec stages 5+6):** the unified error-code taxonomy (e.g. `EMAIL_ALREADY_EXISTS` instead of today's `CONFLICT`, `details` payloads), the `X-Trace-Id` header/middleware, and admin bootstrap-on-startup (`APP_ADMIN_*` env vars, FastAPI `lifespan` hook). This plan wires correct HTTP status codes and functional behavior using the *existing* `DOMAIN_TO_API` error map and manual admin creation via `src/app/actions/run.py`/direct DB fixture in tests — it does not rework either.
- **Env var renames in this plan** follow the spec's Configuration table exactly: `APP_SECURITY_JWT_SECRET`, `APP_SECURITY_ACCESS_TOKEN_EXPIRATION`, `APP_SECURITY_REFRESH_TOKEN_EXPIRATION`, `APP_COOKIE_SECURE`. `APP_ADMIN_*`, `APP_CORS_ALLOWED_ORIGINS`, and `LOG_FORMAT` are out of scope here (Plan 3).
- Pydantic schemas keep this codebase's established convention (from Plan 1): response/request fields are named directly in camelCase in Python (no `alias_generator`). Do not introduce `alias_generator` — that would be an unrelated, larger refactor.

---

### Task 1: Security config — duration parser, JWT secret/TTL env vars, `JWTService` rewrite

**Files:**
- Create: `src/app/core/utils/duration.py`
- Modify: `src/app/core/utils/__init__.py`
- Modify: `src/.env` (local, untracked — not part of the commit)
- Modify: `src/.env.example`
- Modify: `.gitignore` (repo root)
- Modify: `src/configs/config.yaml`
- Modify: `src/app/services/jwt_service.py` (full rewrite)
- Modify: `src/app/core/schemas/token.py`
- Test: `src/tests/test_duration.py`, `src/tests/test_jwt_service.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `parse_duration_seconds(value: str) -> int` (`app.core.utils`). `JWTService.create_access_token(subject: str) -> str`, `create_refresh_token(subject: str) -> str`, `decode_token(token: str, expected_type: str) -> dict`, `hash_token(raw_token: str) -> str` (staticmethod), `access_expire_seconds`/`refresh_expire_seconds` int attributes, module constants `ACCESS_TOKEN_TYPE = "access"` / `REFRESH_TOKEN_TYPE = "refresh"` (`app.services.jwt_service`) — Task 2's `AuthService` and `current_user` dependency consume all of these. `Token(PyModel)` in `app.core.schemas.token` now requires `expiresIn` explicitly (no more broken settings-derived default).
- **Known gap left for Task 2:** `app/services/auth_service.py` (untouched by this task) still calls the *old* `JWTService` API (`create_access_token(data=...)`, `decode_token(token)` with one arg) and constructs `Token(accessToken=...)` relying on the default this task removes. No currently-passing test calls `AuthService.login_user`/`register`, so `pytest tests/` stays green — Task 2 rewrites `auth_service.py` to match the new `JWTService`/`Token` API as part of building the auth flow.

- [ ] **Step 1: Write the failing duration-parser test**

```python
# src/tests/test_duration.py
import pytest

from app.core.utils.duration import parse_duration_seconds


def test_parses_minutes():
    assert parse_duration_seconds("15m") == 900


def test_parses_days():
    assert parse_duration_seconds("30d") == 30 * 86400


def test_parses_seconds_and_hours():
    assert parse_duration_seconds("45s") == 45
    assert parse_duration_seconds("2h") == 7200


def test_rejects_bad_format():
    with pytest.raises(ValueError):
        parse_duration_seconds("15")
    with pytest.raises(ValueError):
        parse_duration_seconds("15x")
```

- [ ] **Step 2: Run it to confirm it fails**

```bash
cd src && python -m pytest tests/test_duration.py -v
```

Expected: `ModuleNotFoundError: No module named 'app.core.utils.duration'`.

- [ ] **Step 3: Implement `app/core/utils/duration.py`**

```python
import re

_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}
_PATTERN = re.compile(r"^(\d+)([smhd])$")


def parse_duration_seconds(value: str) -> int:
    match = _PATTERN.match(value.strip())
    if not match:
        raise ValueError(f"Invalid duration format: {value!r} (expected e.g. '15m', '30d')")
    amount, unit = match.groups()
    return int(amount) * _UNIT_SECONDS[unit]
```

- [ ] **Step 4: Export it from `app/core/utils/__init__.py`**

```python
from .duration import parse_duration_seconds
from .loc2field import loc_to_field
from .paginated import Page, PaginationParams
from .password import check_len_password
from .singleton import Singleton
from .time_format import now_iso_z

__all__ = [
    "Page",
    "PaginationParams",
    "Singleton",
    "check_len_password",
    "loc_to_field",
    "now_iso_z",
    "parse_duration_seconds",
]
```

- [ ] **Step 5: Run the test again — confirm it passes**

```bash
cd src && python -m pytest tests/test_duration.py -v
```

Expected: 4 passed.

- [ ] **Step 6: Update `.gitignore` (repo root) to stop `src/.env` from ever being committed**

`src/.env` holds real secrets and is currently untracked only by omission (no `.gitignore` rule protects it). Add:

```
/.idea
__pycache__/
*.pyc
/src/.env
```

- [ ] **Step 7: Update your local `src/.env`** — rename `RANDOM_SECRET` to `APP_SECURITY_JWT_SECRET` and add the two TTL vars plus the cookie flag (local dev runs over plain HTTP via `docker-compose.yml`, so `APP_COOKIE_SECURE=false` here):

Replace the `RANDOM_SECRET=...` line with:

```
APP_SECURITY_JWT_SECRET=Jf/ZpZSxfMWnOexP48Mp1z200jd+8BVZ7ws6Uw5Jp/w=
APP_SECURITY_ACCESS_TOKEN_EXPIRATION=15m
APP_SECURITY_REFRESH_TOKEN_EXPIRATION=30d
APP_COOKIE_SECURE=false
```

- [ ] **Step 8: Update `src/.env.example`** the same way, but with placeholder secret and the spec's documented default (`true`) plus a comment about local HTTP dev:

Replace the `RANDOM_SECRET=...` line with:

```
# Secret used to sign JWTs - generate your own, e.g. `python -c "import secrets; print(secrets.token_urlsafe(32))"`
APP_SECURITY_JWT_SECRET=change-me-please

# Format: <number><unit>, unit is one of s/m/h/d (e.g. "15m", "30d")
APP_SECURITY_ACCESS_TOKEN_EXPIRATION=15m
APP_SECURITY_REFRESH_TOKEN_EXPIRATION=30d

# Secure flag on the refreshToken cookie. Keep `true` for any real deployment (HTTPS);
# set to `false` only for local dev over plain HTTP (e.g. the bundled docker-compose.yml).
APP_COOKIE_SECURE=true
```

(Also delete the old `RANDOM_SECRET=change-me-please` line if it wasn't already replaced by the block above.)

- [ ] **Step 9: Update `src/configs/config.yaml`** — remove the now-superseded TTL keys from the `token:` block (the two new env vars replace them):

```yaml
token:
  default_type: bearer
  schema: argon2
  access_token:
    algorithm: HS256
```

(Removes `access_token.lifetime_seconds`, `access_token.expire_minutes`, and the whole `refresh_token:` sub-block.)

- [ ] **Step 10: Write the failing `JWTService` tests**

```python
# src/tests/test_jwt_service.py
import jwt
import pytest

from app.core.exceptions.user_exs import InvalidCredentialsError
from app.services.jwt_service import ACCESS_TOKEN_TYPE, REFRESH_TOKEN_TYPE, JWTService


@pytest.fixture
def jwt_service():
    return JWTService()


def test_access_token_has_expected_claims(jwt_service):
    token = jwt_service.create_access_token("user-123")
    payload = jwt.decode(token, jwt_service.secret_key, algorithms=[jwt_service.algorithm])

    assert payload["sub"] == "user-123"
    assert payload["type"] == ACCESS_TOKEN_TYPE
    assert "jti" in payload
    assert "iat" in payload
    assert "exp" in payload


def test_refresh_token_has_refresh_type(jwt_service):
    token = jwt_service.create_refresh_token("user-123")
    payload = jwt.decode(token, jwt_service.secret_key, algorithms=[jwt_service.algorithm])
    assert payload["type"] == REFRESH_TOKEN_TYPE


def test_decode_token_rejects_wrong_type(jwt_service):
    access_token = jwt_service.create_access_token("user-123")
    with pytest.raises(InvalidCredentialsError):
        jwt_service.decode_token(access_token, expected_type=REFRESH_TOKEN_TYPE)


def test_decode_token_rejects_garbage(jwt_service):
    with pytest.raises(InvalidCredentialsError):
        jwt_service.decode_token("not-a-real-token", expected_type=ACCESS_TOKEN_TYPE)


def test_decode_token_accepts_matching_type(jwt_service):
    token = jwt_service.create_access_token("user-123")
    payload = jwt_service.decode_token(token, expected_type=ACCESS_TOKEN_TYPE)
    assert payload["sub"] == "user-123"


def test_hash_token_is_deterministic_sha256():
    h1 = JWTService.hash_token("raw-token-value")
    h2 = JWTService.hash_token("raw-token-value")
    assert h1 == h2
    assert len(h1) == 64


def test_password_hash_roundtrip(jwt_service):
    hashed = jwt_service.get_password_hash("s3cret123")
    assert jwt_service.verify_password("s3cret123", hashed)
    assert not jwt_service.verify_password("wrong", hashed)


def test_expire_seconds_come_from_env_vars(jwt_service):
    assert jwt_service.access_expire_seconds == 15 * 60
    assert jwt_service.refresh_expire_seconds == 30 * 86400
```

- [ ] **Step 11: Run it to confirm it fails**

```bash
cd src && python -m pytest tests/test_jwt_service.py -v
```

Expected: failures — old `JWTService` has no `hash_token`, `create_access_token` requires `data=`, etc.

- [ ] **Step 12: Rewrite `app/services/jwt_service.py`**

```python
import hashlib
import uuid
from datetime import UTC, datetime, timedelta

from passlib.context import CryptContext

import jwt

from app.core.config import settings
from app.core.exceptions.user_exs import InvalidCredentialsError
from app.core.utils import Singleton, parse_duration_seconds

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


class JWTService(Singleton):
    def __init__(self):
        self.pwd_context = CryptContext(schemes=[settings.token.SCHEMA], deprecated="auto")
        self.secret_key = settings.APP_SECURITY_JWT_SECRET
        self.algorithm = settings.token.access_token.ALGORITHM
        self.access_expire_seconds = parse_duration_seconds(settings.APP_SECURITY_ACCESS_TOKEN_EXPIRATION)
        self.refresh_expire_seconds = parse_duration_seconds(settings.APP_SECURITY_REFRESH_TOKEN_EXPIRATION)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return self.pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        return self.pwd_context.hash(password)

    def _create_token(self, subject: str, token_type: str, expire_seconds: int) -> str:
        now = datetime.now(UTC)
        payload = {
            "sub": subject,
            "type": token_type,
            "jti": str(uuid.uuid4()),
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(seconds=expire_seconds)).timestamp()),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_access_token(self, subject: str) -> str:
        return self._create_token(subject, ACCESS_TOKEN_TYPE, self.access_expire_seconds)

    def create_refresh_token(self, subject: str) -> str:
        return self._create_token(subject, REFRESH_TOKEN_TYPE, self.refresh_expire_seconds)

    def decode_token(self, token: str, expected_type: str) -> dict:
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        except jwt.InvalidTokenError as e:
            raise InvalidCredentialsError from e

        if payload.get("sub") is None or payload.get("type") != expected_type:
            raise InvalidCredentialsError
        return payload

    @staticmethod
    def hash_token(raw_token: str) -> str:
        return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
```

- [ ] **Step 13: Fix `app/core/schemas/token.py`'s broken settings-derived default**

```python
from app.core.schemas.base import PyModel


class Token(PyModel):
    accessToken: str
    expiresIn: int
```

- [ ] **Step 14: Run the `JWTService` tests — confirm they pass**

```bash
cd src && python -m pytest tests/test_jwt_service.py -v
```

Expected: 8 passed.

- [ ] **Step 15: Run the full existing suite as a sanity check**

```bash
cd src && python -m pytest tests/ -v
```

Expected: all of Plan 1's tests (`test_app_boot.py`, `test_models.py`, `test_repo_hygiene.py`, `test_unit_of_work.py`) plus this task's two new files pass — nothing regressed. (`app/services/auth_service.py` is not exercised by any of these, so its now-stale calls into the old `JWTService`/`Token` API don't surface yet — see this task's Interfaces note.)

- [ ] **Step 16: Commit**

```bash
git add src/tests/test_duration.py src/tests/test_jwt_service.py src/app/core/utils/duration.py \
  src/app/core/utils/__init__.py src/app/services/jwt_service.py src/app/core/schemas/token.py \
  src/.env.example src/configs/config.yaml .gitignore
git commit -m "feat: JWT secret/TTL env vars, duration parser, rewrite JWTService claims"
```

(`src/.env` is intentionally not added — it's now gitignored.)

---

### Task 2: Auth flow — register/login/refresh/logout

**Files:**
- Modify: `src/app/core/schemas/user.py`
- Modify: `src/app/services/auth_service.py` (full rewrite)
- Modify: `src/app/api/v1/utils/cookies.py` (full rewrite)
- Modify: `src/app/api/v1/dependencies/current_user.py` (full rewrite)
- Modify: `src/app/api/v1/dependencies/__init__.py`
- Modify: `src/app/api/v1/endpoints/auth.py`
- Create: `src/tests/conftest.py`
- Test: `src/tests/test_cookies.py`, `src/tests/test_current_user_dependency.py`, `src/tests/test_auth_service.py`, `src/tests/test_auth_endpoints.py`

**Interfaces:**
- Consumes: `JWTService` from Task 1 (`create_access_token`, `create_refresh_token`, `decode_token`, `hash_token`, `ACCESS_TOKEN_TYPE`/`REFRESH_TOKEN_TYPE`, `access_expire_seconds`/`refresh_expire_seconds`). `UnitOfWork.refresh_token_repo` (`get_by_user_and_hash`, `delete_by_hash`, `delete_all_for_user`, inherited `add`) from Plan 1.
- Produces: `app.core.schemas.user.UserRegisterBody` (email/password/fullName only — no role/isActive, unlike the still-present `UserCreateBody` which Task 3 retires), `UserAndAccessTokenResponse(user, accessToken, expiresIn)`, `UserData` (now the **single** "current principal" type — replaces the old `TokenData`, used by `CurrentUserDep` and everywhere a resolved user is passed around). `AuthService.register(body: UserRegisterBody) -> tuple[UserAndAccessTokenResponse, str, int]` (response, raw refresh token, cookie max-age seconds) — same return shape for `login_user`. `AuthService.refresh_tokens(raw_refresh_token: str) -> tuple[AccessTokenResponse, str, int]`. `AuthService.logout(raw_refresh_token: str) -> None`. `AuthService.verify_access_token(access_token: str) -> UserData`. `app.api.v1.utils.cookies.{REFRESH_COOKIE_NAME, set_refresh_cookie, delete_refresh_cookie}`. `app.api.v1.dependencies.current_user.{CurrentUserDep, AdminUserDep, AdminOrSelfDep}` (`AdminOrSelfDep` is produced here for Task 3's `users.py` to consume — it isn't exercised by any endpoint until then). `tests/conftest.py`'s `db_session_factory`/`client` fixtures — Task 3's HTTP tests and `admin_headers` fixture build on top of these.
- **Known gap left for Task 3:** `src/app/api/v1/endpoints/users.py` is untouched by this task. Its `get_me`/`update_me` handlers still call `user_service.get_current_by_id(...)`, which doesn't exist on `UserService` — this was already broken before this plan (flagged in Plan 1's own notes) and stays broken until Task 3 rewrites `users.py`/`UserService` together. No test in this task hits `/users/*` for that reason; Task 2's HTTP tests only cover `/auth/*`.

- [ ] **Step 1: Write the failing cookie-helper test**

```python
# src/tests/test_cookies.py
from fastapi import Response

from app.api.v1.utils.cookies import REFRESH_COOKIE_NAME, delete_refresh_cookie, set_refresh_cookie


def test_set_refresh_cookie_sets_expected_attributes():
    response = Response()
    set_refresh_cookie(response, "raw-refresh-token", max_age_seconds=2592000)

    cookie_header = response.headers["set-cookie"]
    assert f"{REFRESH_COOKIE_NAME}=raw-refresh-token" in cookie_header
    assert "HttpOnly" in cookie_header
    assert "samesite=lax" in cookie_header.lower()
    assert "Path=/" in cookie_header
    assert "Max-Age=2592000" in cookie_header


def test_delete_refresh_cookie_expires_it():
    response = Response()
    delete_refresh_cookie(response)

    cookie_header = response.headers["set-cookie"]
    assert f"{REFRESH_COOKIE_NAME}=" in cookie_header
    assert "Max-Age=0" in cookie_header
```

- [ ] **Step 2: Run it to confirm it fails**

```bash
cd src && python -m pytest tests/test_cookies.py -v
```

Expected: `ImportError` — `REFRESH_COOKIE_NAME`/`set_refresh_cookie`/`delete_refresh_cookie` don't exist yet (current file only has `set_auth_cookies`/`delete_auth_cookies` for an `access_token` cookie).

- [ ] **Step 3: Rewrite `app/api/v1/utils/cookies.py`**

```python
from fastapi import Response

from app.core.config import settings

REFRESH_COOKIE_NAME = "refreshToken"


def set_refresh_cookie(response: Response, refresh_token: str, max_age_seconds: int) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=max_age_seconds,
        httponly=True,
        secure=bool(settings.APP_COOKIE_SECURE),
        samesite="lax",
        path="/",
    )


def delete_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=bool(settings.APP_COOKIE_SECURE),
        samesite="lax",
    )
```

- [ ] **Step 4: Run the cookie tests — confirm they pass**

```bash
cd src && python -m pytest tests/test_cookies.py -v
```

Expected: 2 passed.

- [ ] **Step 5: Write the failing `current_user` dependency tests**

```python
# src/tests/test_current_user_dependency.py
import uuid

import pytest

from app.api.v1.dependencies.current_user import get_admin_or_self_user, get_admin_user
from app.core.exceptions.user_exs import ForbiddenError
from app.core.schemas.user import UserData, UserRole


def _user(role: UserRole, user_id: uuid.UUID | None = None) -> UserData:
    uid = user_id or uuid.uuid4()
    return UserData(
        id=uid,
        email="u@fish.io",
        fullName="U",
        role=role,
        isActive=True,
        createdAt="2026-01-01T00:00:00Z",
        updatedAt="2026-01-01T00:00:00Z",
        createdBy=uid,
    )


async def test_admin_user_dep_allows_admin():
    admin = _user(UserRole.ADMIN)
    assert await get_admin_user(admin) == admin


async def test_admin_user_dep_rejects_non_admin():
    user = _user(UserRole.USER)
    with pytest.raises(ForbiddenError):
        await get_admin_user(user)


async def test_admin_or_self_allows_admin_for_any_id():
    admin = _user(UserRole.ADMIN)
    other_id = uuid.uuid4()
    assert await get_admin_or_self_user(other_id, admin) == admin


async def test_admin_or_self_allows_self():
    user = _user(UserRole.USER)
    assert await get_admin_or_self_user(user.id, user) == user


async def test_admin_or_self_rejects_other_user():
    user = _user(UserRole.USER)
    other_id = uuid.uuid4()
    with pytest.raises(ForbiddenError):
        await get_admin_or_self_user(other_id, user)
```

- [ ] **Step 6: Run it to confirm it fails**

```bash
cd src && python -m pytest tests/test_current_user_dependency.py -v
```

Expected: `ImportError` — `get_admin_or_self_user` doesn't exist yet, and `UserData` isn't yet importable the way the test expects (current `user.py` has `TokenData`, not a plain-constructible `UserData` used this way — this fails either at collection or first call).

- [ ] **Step 7: Update `app/core/schemas/user.py`** — add `UserRegisterBody`, drop `TokenData` (folded into `UserData`), widen `UserData.role` to non-nullable and `createdBy` to nullable (matches the DB: `role` is `NOT NULL`, `created_by` is nullable), rename `UserWithTokenResponse` to `UserAndAccessTokenResponse` built on the new `AccessTokenResponse`. `UserCreateBody`/`UserUpdateBody` are untouched — `UserCreateBody` is still used by the not-yet-updated `users.py`/`UserService` until Task 3.

```python
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, EmailStr, Field

from app.core.enums import UserRole
from app.core.schemas.base import DatetimeResponse, PyModel
from app.core.schemas.token import AccessTokenResponse
from app.core.utils import check_len_password

__all__ = ["UserRole"]


class UserRegisterBody(PyModel):
    email: Annotated[EmailStr, Field(max_length=254)]
    password: Annotated[str, AfterValidator(check_len_password)]
    fullName: Annotated[str, Field(min_length=2, max_length=200)]


class UserUpdateBody(PyModel):
    fullName: Annotated[str, Field(min_length=2, max_length=200)]
    role: UserRole | None = None
    isActive: bool | None = None


class UserCreateBody(UserUpdateBody):
    email: Annotated[EmailStr, Field(max_length=254)]
    password: Annotated[str, AfterValidator(check_len_password)]
    isActive: bool = True


class UserLoginBody(PyModel):
    email: str
    password: str


class UserData(PyModel):
    id: UUID
    email: EmailStr
    fullName: str
    role: UserRole
    isActive: bool

    createdAt: datetime
    updatedAt: datetime
    createdBy: UUID | None


class UserReadResponse(UserData, DatetimeResponse):
    pass


class UserAndAccessTokenResponse(AccessTokenResponse):
    user: UserReadResponse
```

- [ ] **Step 8: Add `AccessTokenResponse` to `app/core/schemas/token.py`** (keep `Token` — it's still used by nothing new but removing it now would be premature; Task 3 doesn't touch it either, so it simply becomes dead code that a later cleanup could remove — for this plan, leave it defined alongside the new class to avoid hunting down every reference):

```python
from app.core.schemas.base import PyModel


class Token(PyModel):
    accessToken: str
    expiresIn: int


class AccessTokenResponse(PyModel):
    accessToken: str
    expiresIn: int
```

- [ ] **Step 9: Rewrite `app/api/v1/dependencies/current_user.py`**

```python
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request

from app.api.v1.dependencies.services.auth_service import AuthServiceDep
from app.core.exceptions.user_exs import ForbiddenError, InvalidCredentialsError
from app.core.schemas.user import UserData, UserRole


async def get_current_user(request: Request, auth_service: AuthServiceDep) -> UserData:
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise InvalidCredentialsError
    token = auth_header.split(" ", 1)[1]
    return await auth_service.verify_access_token(token)


CurrentUserDep = Annotated[UserData, Depends(get_current_user)]


async def get_admin_user(current_user: CurrentUserDep) -> UserData:  # noqa: RUF029
    if current_user.role != UserRole.ADMIN:
        raise ForbiddenError
    return current_user


async def get_admin_or_self_user(user_id: UUID, current_user: CurrentUserDep) -> UserData:  # noqa: RUF029
    if current_user.role != UserRole.ADMIN and current_user.id != user_id:
        raise ForbiddenError
    return current_user


AdminUserDep = Annotated[UserData, Depends(get_admin_user)]
AdminOrSelfDep = Annotated[UserData, Depends(get_admin_or_self_user)]
```

(This drops the old access-token cookie fallback entirely — per spec, the access token only ever travels via the `Authorization: Bearer` header — and drops `AnyViewUserDep`/`_user_has_role`, which nothing outside this file used.)

- [ ] **Step 10: Update `app/api/v1/dependencies/__init__.py`**

```python
from .current_user import AdminOrSelfDep, AdminUserDep, CurrentUserDep
from .pagination import PaginationDep
from .services import (
    AuthServiceDep,
    UserServiceDep,
)
from .session import SessionDep
from .uow import UnitOfWorkDep

__all__ = [
    "AdminOrSelfDep",
    "AdminUserDep",
    "AuthServiceDep",
    "CurrentUserDep",
    "PaginationDep",
    "SessionDep",
    "UnitOfWorkDep",
    "UserServiceDep",
]
```

- [ ] **Step 11: Run the dependency tests — confirm they pass**

```bash
cd src && python -m pytest tests/test_current_user_dependency.py -v
```

Expected: 5 passed.

- [ ] **Step 12: Write the failing `AuthService` tests** (direct service tests against an in-memory `UnitOfWork`, same pattern as Plan 1's `test_unit_of_work.py` — no HTTP layer involved yet)

```python
# src/tests/test_auth_service.py
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.exceptions.user_exs import (
    InvalidCredentialsError,
    InvalidPasswordError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from app.core.schemas.user import UserLoginBody, UserRegisterBody
from app.infrastructure.models import Base
from app.infrastructure.unit_of_work import UnitOfWork
from app.services.auth_service import AuthService
from app.services.jwt_service import JWTService


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


def _auth_service(session):
    return AuthService(UnitOfWork(session), JWTService())


async def test_register_creates_user_and_returns_token_pair(session_factory):
    async with session_factory() as session:
        service = _auth_service(session)
        body = UserRegisterBody(email="new@fish.io", password="password1", fullName="New Fish")

        response, refresh_token, max_age = await service.register(body)

        assert response.user.email == "new@fish.io"
        assert response.user.role.value == "USER"
        assert response.user.createdBy == response.user.id
        assert response.accessToken
        assert refresh_token
        assert max_age > 0


async def test_register_rejects_duplicate_email(session_factory):
    async with session_factory() as session:
        service = _auth_service(session)
        await service.register(UserRegisterBody(email="dup@fish.io", password="password1", fullName="Fish One"))

    async with session_factory() as session:
        service = _auth_service(session)
        with pytest.raises(UserAlreadyExistsError):
            await service.register(UserRegisterBody(email="dup@fish.io", password="password2", fullName="Fish Two"))


async def test_login_with_correct_credentials_returns_token_pair(session_factory):
    async with session_factory() as session:
        service = _auth_service(session)
        await service.register(UserRegisterBody(email="login@fish.io", password="password1", fullName="Login Fish"))

    async with session_factory() as session:
        service = _auth_service(session)
        response, refresh_token, _ = await service.login_user(
            UserLoginBody(email="login@fish.io", password="password1")
        )
        assert response.user.email == "login@fish.io"
        assert refresh_token


async def test_login_with_wrong_password_raises(session_factory):
    async with session_factory() as session:
        service = _auth_service(session)
        await service.register(UserRegisterBody(email="wrongpw@fish.io", password="password1", fullName="Fish"))

    async with session_factory() as session:
        service = _auth_service(session)
        with pytest.raises(InvalidPasswordError):
            await service.login_user(UserLoginBody(email="wrongpw@fish.io", password="wrong-password"))


async def test_login_with_unknown_email_raises(session_factory):
    async with session_factory() as session:
        service = _auth_service(session)
        with pytest.raises(UserNotFoundError):
            await service.login_user(UserLoginBody(email="ghost@fish.io", password="password1"))


async def test_refresh_rotates_token_and_invalidates_old_one(session_factory):
    async with session_factory() as session:
        service = _auth_service(session)
        _, refresh_token, _ = await service.register(
            UserRegisterBody(email="rotate@fish.io", password="password1", fullName="Fish")
        )

    async with session_factory() as session:
        service = _auth_service(session)
        new_access, new_refresh, _ = await service.refresh_tokens(refresh_token)
        assert new_access.accessToken
        assert new_refresh != refresh_token

    async with session_factory() as session:
        service = _auth_service(session)
        with pytest.raises(InvalidCredentialsError):
            await service.refresh_tokens(refresh_token)


async def test_refresh_with_unknown_token_raises(session_factory):
    async with session_factory() as session:
        service = _auth_service(session)
        with pytest.raises(InvalidCredentialsError):
            await service.refresh_tokens("not-a-real-refresh-token")


async def test_logout_deletes_refresh_token_and_is_idempotent(session_factory):
    async with session_factory() as session:
        service = _auth_service(session)
        _, refresh_token, _ = await service.register(
            UserRegisterBody(email="logout@fish.io", password="password1", fullName="Fish")
        )

    async with session_factory() as session:
        service = _auth_service(session)
        await service.logout(refresh_token)

    async with session_factory() as session:
        service = _auth_service(session)
        with pytest.raises(InvalidCredentialsError):
            await service.refresh_tokens(refresh_token)

    async with session_factory() as session:
        service = _auth_service(session)
        await service.logout(refresh_token)  # idempotent — no error


async def test_verify_access_token_returns_current_user_data(session_factory):
    async with session_factory() as session:
        service = _auth_service(session)
        response, _, _ = await service.register(
            UserRegisterBody(email="verify@fish.io", password="password1", fullName="Fish")
        )
        access_token = response.accessToken

    async with session_factory() as session:
        service = _auth_service(session)
        user_data = await service.verify_access_token(access_token)
        assert user_data.email == "verify@fish.io"
```

- [ ] **Step 13: Run it to confirm it fails**

```bash
cd src && python -m pytest tests/test_auth_service.py -v
```

Expected: failures — `AuthService.register` still takes a `UserCreateBody`, has no `refresh_tokens`/`logout`/`verify_access_token`, etc.

- [ ] **Step 14: Rewrite `app/services/auth_service.py`**

```python
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.core.enums import UserRole
from app.core.exceptions.user_exs import (
    InvalidCredentialsError,
    InvalidPasswordError,
    UserAlreadyExistsError,
    UserNotActiveError,
    UserNotFoundError,
)
from app.core.schemas.token import AccessTokenResponse
from app.core.schemas.user import UserAndAccessTokenResponse, UserData, UserLoginBody, UserReadResponse, UserRegisterBody
from app.infrastructure.models import RefreshToken, User
from app.infrastructure.unit_of_work import UnitOfWork
from app.services.jwt_service import ACCESS_TOKEN_TYPE, REFRESH_TOKEN_TYPE, JWTService


def _expiry(seconds: int) -> datetime:
    return datetime.now(UTC) + timedelta(seconds=seconds)


class AuthService:
    def __init__(self, uow: UnitOfWork, jwt_service: JWTService):
        self.uow = uow
        self.jwt_service = jwt_service

    @staticmethod
    def _to_read_response(user: User) -> UserReadResponse:
        return UserReadResponse(
            id=user.id,
            email=user.email,
            fullName=user.full_name,
            role=user.role,
            isActive=user.is_active,
            createdAt=user.created_at,
            updatedAt=user.updated_at,
            createdBy=user.created_by,
        )

    async def _authenticate_user(self, email: str, password: str) -> User:
        user = await self.uow.user_repo.get_by_email(email)
        if user is None:
            raise UserNotFoundError
        if not self.jwt_service.verify_password(password, str(user.password)):
            raise InvalidPasswordError
        if not user.is_active:
            raise UserNotActiveError
        return user

    async def _issue_token_pair(self, user: User) -> tuple[UserAndAccessTokenResponse, str, int]:
        access_token = self.jwt_service.create_access_token(str(user.id))
        refresh_token = self.jwt_service.create_refresh_token(str(user.id))
        max_age = self.jwt_service.refresh_expire_seconds

        await self.uow.refresh_token_repo.add(
            RefreshToken(
                user_id=user.id,
                hashed_token=self.jwt_service.hash_token(refresh_token),
                expires_at=_expiry(max_age),
            )
        )

        response = UserAndAccessTokenResponse(
            accessToken=access_token,
            expiresIn=self.jwt_service.access_expire_seconds,
            user=self._to_read_response(user),
        )
        return response, refresh_token, max_age

    async def register(self, user_data: UserRegisterBody) -> tuple[UserAndAccessTokenResponse, str, int]:
        async with self.uow:
            existing_user = await self.uow.user_repo.get_by_email(user_data.email)
            if existing_user:
                raise UserAlreadyExistsError

            hashed_password = self.jwt_service.get_password_hash(user_data.password)
            user = await self.uow.user_repo.add(
                User(
                    email=user_data.email,
                    password=hashed_password,
                    full_name=user_data.fullName,
                    role=UserRole.USER,
                    is_active=True,
                )
            )
            user = await self.uow.user_repo.update(user.id, {"created_by": user.id})
            return await self._issue_token_pair(user)

    async def login_user(self, login_body: UserLoginBody) -> tuple[UserAndAccessTokenResponse, str, int]:
        async with self.uow:
            user = await self._authenticate_user(login_body.email, login_body.password)
            return await self._issue_token_pair(user)

    async def refresh_tokens(self, raw_refresh_token: str) -> tuple[AccessTokenResponse, str, int]:
        async with self.uow:
            payload = self.jwt_service.decode_token(raw_refresh_token, expected_type=REFRESH_TOKEN_TYPE)
            user_id = UUID(payload["sub"])
            hashed = self.jwt_service.hash_token(raw_refresh_token)

            stored = await self.uow.refresh_token_repo.get_by_user_and_hash(user_id, hashed)
            if stored is None or stored.expires_at < datetime.now(UTC):
                raise InvalidCredentialsError

            user = await self.uow.user_repo.get_by_id(user_id)
            if user is None or not user.is_active:
                raise InvalidCredentialsError

            await self.uow.refresh_token_repo.delete_by_hash(hashed)

            new_access_token = self.jwt_service.create_access_token(str(user.id))
            new_refresh_token = self.jwt_service.create_refresh_token(str(user.id))
            max_age = self.jwt_service.refresh_expire_seconds

            await self.uow.refresh_token_repo.add(
                RefreshToken(
                    user_id=user.id,
                    hashed_token=self.jwt_service.hash_token(new_refresh_token),
                    expires_at=_expiry(max_age),
                )
            )

            response = AccessTokenResponse(
                accessToken=new_access_token,
                expiresIn=self.jwt_service.access_expire_seconds,
            )
            return response, new_refresh_token, max_age

    async def logout(self, raw_refresh_token: str) -> None:
        async with self.uow:
            hashed = self.jwt_service.hash_token(raw_refresh_token)
            await self.uow.refresh_token_repo.delete_by_hash(hashed)

    async def verify_access_token(self, access_token: str) -> UserData:
        async with self.uow:
            payload = self.jwt_service.decode_token(access_token, expected_type=ACCESS_TOKEN_TYPE)
            user_id = UUID(payload["sub"])
            user = await self.uow.user_repo.get_by_id(user_id)
            if not user or not user.is_active:
                raise InvalidCredentialsError
            return UserData(
                id=user.id,
                email=user.email,
                fullName=user.full_name,
                role=user.role,
                isActive=user.is_active,
                createdAt=user.created_at,
                updatedAt=user.updated_at,
                createdBy=user.created_by,
            )
```

- [ ] **Step 15: Run the `AuthService` tests — confirm they pass**

```bash
cd src && python -m pytest tests/test_auth_service.py -v
```

Expected: 9 passed.

- [ ] **Step 16: Create `src/tests/conftest.py`** with a shared in-memory-SQLite `TestClient` fixture (overrides the app's real Postgres session dependency; used by this task's HTTP tests and extended by Task 3)

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.infrastructure.database.db_helper import db_helper
from app.infrastructure.models import Base
from app.main import app


@pytest.fixture
async def db_session_factory():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.fixture
async def client(db_session_factory):
    async def override_session_getter():
        async with db_session_factory() as session:
            yield session

    app.dependency_overrides[db_helper.session_getter] = override_session_getter

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
```

- [ ] **Step 17: Write the failing auth-flow HTTP tests**

```python
# src/tests/test_auth_endpoints.py
def test_register_returns_201_sets_cookie_and_location_header(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "flow@fish.io", "password": "password1", "fullName": "Flow Fish"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["user"]["email"] == "flow@fish.io"
    assert body["user"]["role"] == "USER"
    assert response.headers["location"] == f"/api/v1/users/{body['user']['id']}"
    assert "refreshToken" in response.cookies


def test_register_rejects_duplicate_email(client):
    payload = {"email": "dup@fish.io", "password": "password1", "fullName": "Fish"}
    client.post("/api/v1/auth/register", json=payload)
    response = client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 409


def test_login_returns_200_and_sets_refresh_cookie(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "login@fish.io", "password": "password1", "fullName": "Login Fish"},
    )

    response = client.post("/api/v1/auth/login", json={"email": "login@fish.io", "password": "password1"})

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "login@fish.io"
    assert "refreshToken" in response.cookies


def test_login_with_wrong_password_returns_401(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "badpw@fish.io", "password": "password1", "fullName": "Fish"},
    )

    response = client.post("/api/v1/auth/login", json={"email": "badpw@fish.io", "password": "wrong-password"})
    assert response.status_code == 401


def test_refresh_rotates_cookie_and_invalidates_previous_refresh_token(client):
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "rotate@fish.io", "password": "password1", "fullName": "Fish"},
    )
    old_refresh_cookie = register_response.cookies["refreshToken"]

    refresh_response = client.post("/api/v1/auth/refresh")
    assert refresh_response.status_code == 200
    assert "accessToken" in refresh_response.json()
    new_refresh_cookie = refresh_response.cookies["refreshToken"]
    assert new_refresh_cookie != old_refresh_cookie

    client.cookies.set("refreshToken", old_refresh_cookie)
    reuse_response = client.post("/api/v1/auth/refresh")
    assert reuse_response.status_code == 401


def test_refresh_without_cookie_returns_401(client):
    response = client.post("/api/v1/auth/refresh")
    assert response.status_code == 401


def test_logout_clears_cookie_and_revokes_refresh_token(client):
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "logout@fish.io", "password": "password1", "fullName": "Fish"},
    )
    refresh_cookie = register_response.cookies["refreshToken"]

    logout_response = client.post("/api/v1/auth/logout")
    assert logout_response.status_code == 204

    client.cookies.set("refreshToken", refresh_cookie)
    reuse_response = client.post("/api/v1/auth/refresh")
    assert reuse_response.status_code == 401


def test_logout_without_cookie_returns_401(client):
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 401
```

- [ ] **Step 18: Run it to confirm it fails**

```bash
cd src && python -m pytest tests/test_auth_endpoints.py -v
```

Expected: failures — `/auth/register`, `/auth/refresh`, `/auth/logout` don't exist yet (404), and `/auth/login` doesn't set a `refreshToken` cookie.

- [ ] **Step 19: Rewrite `app/api/v1/endpoints/auth.py`**

```python
from fastapi import APIRouter, Request, Response, status

from app.api.v1.dependencies import AuthServiceDep
from app.api.v1.utils.cookies import REFRESH_COOKIE_NAME, delete_refresh_cookie, set_refresh_cookie
from app.core.exceptions.user_exs import InvalidCredentialsError
from app.core.schemas.token import AccessTokenResponse
from app.core.schemas.user import UserAndAccessTokenResponse, UserLoginBody, UserRegisterBody

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserAndAccessTokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    auth_service: AuthServiceDep,
    user_data: UserRegisterBody,
    response: Response,
) -> UserAndAccessTokenResponse:
    result, refresh_token, max_age = await auth_service.register(user_data)
    set_refresh_cookie(response, refresh_token, max_age_seconds=max_age)
    response.headers["Location"] = f"/api/v1/users/{result.user.id}"
    return result


@router.post("/login", response_model=UserAndAccessTokenResponse, status_code=status.HTTP_200_OK)
async def login(
    auth_service: AuthServiceDep,
    user_data: UserLoginBody,
    response: Response,
) -> UserAndAccessTokenResponse:
    result, refresh_token, max_age = await auth_service.login_user(user_data)
    set_refresh_cookie(response, refresh_token, max_age_seconds=max_age)
    return result


@router.post("/refresh", response_model=AccessTokenResponse, status_code=status.HTTP_200_OK)
async def refresh(
    auth_service: AuthServiceDep,
    request: Request,
    response: Response,
) -> AccessTokenResponse:
    raw_refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_refresh_token:
        raise InvalidCredentialsError

    result, new_refresh_token, max_age = await auth_service.refresh_tokens(raw_refresh_token)
    set_refresh_cookie(response, new_refresh_token, max_age_seconds=max_age)
    return result


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    auth_service: AuthServiceDep,
    request: Request,
    response: Response,
) -> None:
    raw_refresh_token = request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_refresh_token:
        raise InvalidCredentialsError
    await auth_service.logout(raw_refresh_token)
    delete_refresh_cookie(response)
```

- [ ] **Step 20: Run the auth-endpoint tests — confirm they pass**

```bash
cd src && python -m pytest tests/test_auth_endpoints.py -v
```

Expected: 8 passed.

- [ ] **Step 21: Run the full suite as a sanity check**

```bash
cd src && python -m pytest tests/ -v
```

Expected: everything from Plan 1 plus Task 1 plus this task's five new test files passes. `src/app/api/v1/endpoints/users.py` still 500s on `/users/me` if actually called — untouched, unexercised, as noted in this task's Interfaces.

- [ ] **Step 22: Commit**

```bash
git add src/tests/conftest.py src/tests/test_cookies.py src/tests/test_current_user_dependency.py \
  src/tests/test_auth_service.py src/tests/test_auth_endpoints.py \
  src/app/core/schemas/user.py src/app/core/schemas/token.py src/app/services/auth_service.py \
  src/app/api/v1/utils/cookies.py src/app/api/v1/dependencies/current_user.py \
  src/app/api/v1/dependencies/__init__.py src/app/api/v1/endpoints/auth.py
git commit -m "feat: implement register/login/refresh/logout with refresh-token rotation"
```

---

### Task 3: Users CRUD — pagination, filters, RBAC, ownership, soft-delete

**Files:**
- Modify: `src/app/core/schemas/user.py` (add `AdminRegisterUserBody`, `UserFilterQuery`; remove now-dead `UserCreateBody`)
- Modify: `src/app/core/utils/paginated.py` (defaults: `page` 0, `size` 20/max 100)
- Modify: `src/app/api/v1/dependencies/pagination.py` (defaults: `size` 20/max 100)
- Create: `src/app/api/v1/dependencies/user_filters.py`
- Modify: `src/app/api/v1/dependencies/__init__.py`
- Modify: `src/app/infrastructure/repositories/user_repository.py`
- Modify: `src/app/services/user_service.py` (full rewrite)
- Modify: `src/app/api/v1/endpoints/users.py` (full rewrite)
- Modify: `src/tests/conftest.py` (add `admin_headers` fixture)
- Test: `src/tests/test_user_repository_filters.py`, `src/tests/test_user_service.py`, `src/tests/test_users_endpoints.py`

**Interfaces:**
- Consumes: `AdminOrSelfDep`, `AdminUserDep`, `CurrentUserDep` from Task 2. `UnitOfWork.refresh_token_repo.delete_all_for_user` from Plan 1 (used for session revocation on deactivation).
- Produces: `UserFilterQuery(email, fullName, role, isActive, createdFrom, createdTo)` and `AdminRegisterUserBody(email, password, fullName, role=USER, isActive=True)` (`app.core.schemas.user`). `UserRepository.get_filtered(filters, offset, limit) -> list[User]` / `count_filtered(filters) -> int`. `UserService.create_user(data: AdminRegisterUserBody) -> UserReadResponse`, `get_all_users(pagination, filters) -> Page[UserReadResponse]`, `update_user(user_id, new_data: UserUpdateBody, acting_user: UserData) -> UserReadResponse` (enforces the ownership rule), `deactivate_by_id(user_id)` (now also revokes refresh tokens). Fixed `GET/PUT /users/{user_id}` routes (previously `/{id}` with a mismatched `user_id` function parameter — a genuine pre-existing bug where the path parameter never bound, silently becoming a required *query* param instead; verify with `python -c "..."` + `app.openapi()` before/after if you want to see the bug for yourself).

- [ ] **Step 1: Write the failing repository-filter tests**

```python
# src/tests/test_user_repository_filters.py
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.enums import UserRole
from app.core.schemas.user import UserFilterQuery
from app.infrastructure.models import Base, User
from app.infrastructure.repositories import UserRepository


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


async def _make_user(repo, **overrides):
    now = datetime.now(UTC)
    defaults = dict(
        id=uuid.uuid4(),
        email="user@example.com",
        password="hashed",
        full_name="Some User",
        role=UserRole.USER,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    defaults.update(overrides)
    return await repo.add(User(**defaults))


async def test_email_and_full_name_filters_are_case_insensitive_contains(session_factory):
    async with session_factory() as session:
        repo = UserRepository(session)
        await _make_user(repo, email="alice@fish.io", full_name="Alice Fisher")
        await _make_user(repo, email="bob@fish.io", full_name="Bob Carp")
        await session.commit()

        results = await repo.get_filtered(UserFilterQuery(email="ALICE"), offset=0, limit=10)
        assert [u.email for u in results] == ["alice@fish.io"]

        results = await repo.get_filtered(UserFilterQuery(fullName="carp"), offset=0, limit=10)
        assert [u.email for u in results] == ["bob@fish.io"]


async def test_role_and_is_active_filters_are_exact_match(session_factory):
    async with session_factory() as session:
        repo = UserRepository(session)
        await _make_user(repo, email="admin@fish.io", role=UserRole.ADMIN)
        await _make_user(repo, email="inactive@fish.io", is_active=False)
        await session.commit()

        results = await repo.get_filtered(UserFilterQuery(role=UserRole.ADMIN), offset=0, limit=10)
        assert [u.email for u in results] == ["admin@fish.io"]

        results = await repo.get_filtered(UserFilterQuery(isActive=False), offset=0, limit=10)
        assert [u.email for u in results] == ["inactive@fish.io"]


async def test_created_at_range_filter_is_inclusive(session_factory):
    async with session_factory() as session:
        repo = UserRepository(session)
        base = datetime(2026, 1, 1, tzinfo=UTC)
        await _make_user(repo, email="early@fish.io", created_at=base - timedelta(days=10))
        await _make_user(repo, email="mid@fish.io", created_at=base)
        await _make_user(repo, email="late@fish.io", created_at=base + timedelta(days=10))
        await session.commit()

        results = await repo.get_filtered(
            UserFilterQuery(createdFrom=base, createdTo=base + timedelta(days=10)), offset=0, limit=10
        )
        assert {u.email for u in results} == {"mid@fish.io", "late@fish.io"}


async def test_results_sorted_active_desc_then_created_at_desc(session_factory):
    async with session_factory() as session:
        repo = UserRepository(session)
        base = datetime(2026, 1, 1, tzinfo=UTC)
        await _make_user(repo, email="old_active@fish.io", is_active=True, created_at=base)
        await _make_user(repo, email="new_active@fish.io", is_active=True, created_at=base + timedelta(days=1))
        await _make_user(repo, email="new_inactive@fish.io", is_active=False, created_at=base + timedelta(days=2))
        await session.commit()

        results = await repo.get_filtered(UserFilterQuery(), offset=0, limit=10)
        assert [u.email for u in results] == [
            "new_active@fish.io",
            "old_active@fish.io",
            "new_inactive@fish.io",
        ]


async def test_count_filtered_matches_filtered_results(session_factory):
    async with session_factory() as session:
        repo = UserRepository(session)
        await _make_user(repo, email="a@fish.io", role=UserRole.ADMIN)
        await _make_user(repo, email="b@fish.io", role=UserRole.USER)
        await session.commit()

        assert await repo.count_filtered(UserFilterQuery(role=UserRole.ADMIN)) == 1
        assert await repo.count_filtered(UserFilterQuery()) == 2
```

- [ ] **Step 2: Run it to confirm it fails**

```bash
cd src && python -m pytest tests/test_user_repository_filters.py -v
```

Expected: `ImportError` — `UserFilterQuery` doesn't exist yet, `get_filtered`/`count_filtered` don't exist on `UserRepository`.

- [ ] **Step 3: Add `UserFilterQuery` and `AdminRegisterUserBody` to `app/core/schemas/user.py`, remove `UserCreateBody`**

Full file:

```python
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, EmailStr, Field

from app.core.enums import UserRole
from app.core.schemas.base import DatetimeResponse, PyModel
from app.core.schemas.token import AccessTokenResponse
from app.core.utils import check_len_password

__all__ = ["UserRole"]


class UserRegisterBody(PyModel):
    email: Annotated[EmailStr, Field(max_length=254)]
    password: Annotated[str, AfterValidator(check_len_password)]
    fullName: Annotated[str, Field(min_length=2, max_length=200)]


class UserUpdateBody(PyModel):
    fullName: Annotated[str, Field(min_length=2, max_length=200)]
    role: UserRole | None = None
    isActive: bool | None = None


class AdminRegisterUserBody(UserRegisterBody):
    role: UserRole = UserRole.USER
    isActive: bool = True


class UserLoginBody(PyModel):
    email: str
    password: str


class UserData(PyModel):
    id: UUID
    email: EmailStr
    fullName: str
    role: UserRole
    isActive: bool

    createdAt: datetime
    updatedAt: datetime
    createdBy: UUID | None


class UserReadResponse(UserData, DatetimeResponse):
    pass


class UserAndAccessTokenResponse(AccessTokenResponse):
    user: UserReadResponse


class UserFilterQuery(PyModel):
    email: str | None = None
    fullName: str | None = None
    role: UserRole | None = None
    isActive: bool | None = None
    createdFrom: datetime | None = None
    createdTo: datetime | None = None
```

- [ ] **Step 4: Add `get_filtered`/`count_filtered` to `app/infrastructure/repositories/user_repository.py`**

```python
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.base import RepositoryError
from app.core.schemas.user import UserFilterQuery
from app.infrastructure.models import User
from app.infrastructure.repositories.base_repo import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, model=User)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        try:
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def update(self, user_id: UUID, data: dict[str, Any]) -> User | None:
        data["updated_at"] = datetime.now(UTC)
        return await super().update(user_id, data)

    async def get_filtered(self, filters: UserFilterQuery, offset: int, limit: int) -> list[User]:
        stmt = self._apply_filters(select(User), filters)
        stmt = stmt.order_by(User.is_active.desc(), User.created_at.desc()).offset(offset).limit(limit)
        try:
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def count_filtered(self, filters: UserFilterQuery) -> int:
        stmt = self._apply_filters(select(func.count()).select_from(User), filters)
        try:
            result = await self.session.execute(stmt)
            return result.scalar_one()
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    @staticmethod
    def _apply_filters(stmt: Select, filters: UserFilterQuery) -> Select:
        if filters.email:
            stmt = stmt.where(User.email.ilike(f"%{filters.email}%"))
        if filters.fullName:
            stmt = stmt.where(User.full_name.ilike(f"%{filters.fullName}%"))
        if filters.role is not None:
            stmt = stmt.where(User.role == filters.role)
        if filters.isActive is not None:
            stmt = stmt.where(User.is_active == filters.isActive)
        if filters.createdFrom is not None:
            stmt = stmt.where(User.created_at >= filters.createdFrom)
        if filters.createdTo is not None:
            stmt = stmt.where(User.created_at <= filters.createdTo)
        return stmt
```

- [ ] **Step 5: Run the repository-filter tests — confirm they pass**

```bash
cd src && python -m pytest tests/test_user_repository_filters.py -v
```

Expected: 5 passed.

- [ ] **Step 6: Write the failing `UserService` tests**

```python
# src/tests/test_user_service.py
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.enums import UserRole
from app.core.exceptions.user_exs import ForbiddenError, UserAlreadyExistsError, UserNotFoundError
from app.core.schemas.user import AdminRegisterUserBody, UserData, UserFilterQuery, UserUpdateBody
from app.core.utils.paginated import PaginationParams
from app.infrastructure.models import Base, RefreshToken
from app.infrastructure.unit_of_work import UnitOfWork
from app.services.jwt_service import JWTService
from app.services.user_service import UserService


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


def _service(session):
    return UserService(UnitOfWork(session), JWTService())


def _admin_principal(user_id: uuid.UUID) -> UserData:
    return UserData(
        id=user_id, email="admin@fish.io", fullName="Admin", role=UserRole.ADMIN, isActive=True,
        createdAt="2026-01-01T00:00:00Z", updatedAt="2026-01-01T00:00:00Z", createdBy=user_id,
    )


async def test_create_user_allows_arbitrary_role(session_factory):
    async with session_factory() as session:
        service = _service(session)
        body = AdminRegisterUserBody(email="admin2@fish.io", password="password1", fullName="Fish", role=UserRole.ADMIN)
        created = await service.create_user(body)
        assert created.role == UserRole.ADMIN
        assert created.createdBy == created.id


async def test_create_user_rejects_duplicate_email(session_factory):
    async with session_factory() as session:
        service = _service(session)
        body = AdminRegisterUserBody(email="dup2@fish.io", password="password1", fullName="Fish")
        await service.create_user(body)

    async with session_factory() as session:
        service = _service(session)
        with pytest.raises(UserAlreadyExistsError):
            await service.create_user(AdminRegisterUserBody(email="dup2@fish.io", password="password1", fullName="Fish"))


async def test_get_by_id_raises_when_missing(session_factory):
    async with session_factory() as session:
        service = _service(session)
        with pytest.raises(UserNotFoundError):
            await service.get_by_id(uuid.uuid4())


async def test_self_update_of_full_name_is_allowed(session_factory):
    async with session_factory() as session:
        service = _service(session)
        created = await service.create_user(AdminRegisterUserBody(email="self@fish.io", password="password1", fullName="Old Name"))
        self_principal = UserData(
            id=created.id, email=created.email, fullName=created.fullName, role=UserRole.USER, isActive=True,
            createdAt="2026-01-01T00:00:00Z", updatedAt="2026-01-01T00:00:00Z", createdBy=created.id,
        )

    async with session_factory() as session:
        service = _service(session)
        updated = await service.update_user(created.id, UserUpdateBody(fullName="New Name"), acting_user=self_principal)
        assert updated.fullName == "New Name"


async def test_self_cannot_change_own_role_or_is_active(session_factory):
    async with session_factory() as session:
        service = _service(session)
        created = await service.create_user(AdminRegisterUserBody(email="escalate@fish.io", password="password1", fullName="Fish"))
        self_principal = UserData(
            id=created.id, email=created.email, fullName=created.fullName, role=UserRole.USER, isActive=True,
            createdAt="2026-01-01T00:00:00Z", updatedAt="2026-01-01T00:00:00Z", createdBy=created.id,
        )

    async with session_factory() as session:
        service = _service(session)
        with pytest.raises(ForbiddenError):
            await service.update_user(
                created.id, UserUpdateBody(fullName="Fish", role=UserRole.ADMIN), acting_user=self_principal
            )


async def test_admin_can_change_role_and_is_active(session_factory):
    async with session_factory() as session:
        service = _service(session)
        created = await service.create_user(AdminRegisterUserBody(email="promote@fish.io", password="password1", fullName="Fish"))

    async with session_factory() as session:
        service = _service(session)
        admin = _admin_principal(uuid.uuid4())
        updated = await service.update_user(
            created.id, UserUpdateBody(fullName="Fish", role=UserRole.ADMIN, isActive=True), acting_user=admin
        )
        assert updated.role == UserRole.ADMIN


async def test_deactivate_revokes_all_refresh_tokens(session_factory):
    async with session_factory() as session:
        service = _service(session)
        created = await service.create_user(AdminRegisterUserBody(email="revoke@fish.io", password="password1", fullName="Fish"))

    async with session_factory() as session:
        await session.execute(
            RefreshToken.__table__.insert().values(
                id=uuid.uuid4(),
                user_id=created.id,
                hashed_token="somehash",
                expires_at=datetime.now(UTC) + timedelta(days=1),
                created_at=datetime.now(UTC),
            )
        )
        await session.commit()

    async with session_factory() as session:
        service = _service(session)
        await service.deactivate_by_id(created.id)

    async with session_factory() as session:
        uow = UnitOfWork(session)
        async with uow:
            remaining = await uow.refresh_token_repo.get_by_user_and_hash(created.id, "somehash")
            assert remaining is None


async def test_get_all_users_applies_pagination_and_filters(session_factory):
    async with session_factory() as session:
        service = _service(session)
        await service.create_user(AdminRegisterUserBody(email="page1@fish.io", password="password1", fullName="Fish One"))
        await service.create_user(AdminRegisterUserBody(email="page2@fish.io", password="password1", fullName="Fish Two"))

    async with session_factory() as session:
        service = _service(session)
        page = await service.get_all_users(PaginationParams(page=0, size=20), UserFilterQuery(email="page1"))
        assert page.total == 1
        assert page.items[0].email == "page1@fish.io"
```

- [ ] **Step 7: Run it to confirm it fails**

```bash
cd src && python -m pytest tests/test_user_service.py -v
```

Expected: failures — `UserService.create_user`/`update_user` (this signature)/`get_all_users` (this signature) don't exist yet.

- [ ] **Step 8: Rewrite `app/services/user_service.py`**

```python
from datetime import UTC, datetime
from uuid import UUID

from app.core.enums import UserRole
from app.core.exceptions.user_exs import ForbiddenError, UserAlreadyExistsError, UserNotFoundError
from app.core.schemas.user import (
    AdminRegisterUserBody,
    UserData,
    UserFilterQuery,
    UserReadResponse,
    UserUpdateBody,
)
from app.core.utils.paginated import Page, PaginationParams
from app.infrastructure.models import User
from app.infrastructure.unit_of_work import UnitOfWork
from app.services.jwt_service import JWTService


class UserService:
    def __init__(self, uow: UnitOfWork, jwt_service: JWTService):
        self.uow = uow
        self.jwt_service = jwt_service

    @staticmethod
    def _to_read_response(user: User) -> UserReadResponse:
        return UserReadResponse(
            id=user.id,
            email=user.email,
            fullName=user.full_name,
            role=user.role,
            isActive=user.is_active,
            createdAt=user.created_at,
            updatedAt=user.updated_at,
            createdBy=user.created_by,
        )

    async def get_all_users(self, pagination: PaginationParams, filters: UserFilterQuery) -> Page[UserReadResponse]:
        async with self.uow:
            users = await self.uow.user_repo.get_filtered(filters, offset=pagination.offset, limit=pagination.limit)
            total = await self.uow.user_repo.count_filtered(filters)
            items = [self._to_read_response(u) for u in users]
            return Page.build(items=items, total=total, pagination=pagination)

    async def get_by_id(self, user_id: UUID) -> UserReadResponse:
        async with self.uow:
            user = await self.uow.user_repo.get_by_id(user_id)
            if not user:
                raise UserNotFoundError
            return self._to_read_response(user)

    async def create_user(self, data: AdminRegisterUserBody) -> UserReadResponse:
        async with self.uow:
            existing = await self.uow.user_repo.get_by_email(data.email)
            if existing:
                raise UserAlreadyExistsError

            hashed_password = self.jwt_service.get_password_hash(data.password)
            user = await self.uow.user_repo.add(
                User(
                    email=data.email,
                    password=hashed_password,
                    full_name=data.fullName,
                    role=data.role,
                    is_active=data.isActive,
                )
            )
            user = await self.uow.user_repo.update(user.id, {"created_by": user.id})
            return self._to_read_response(user)

    async def update_user(self, user_id: UUID, new_data: UserUpdateBody, acting_user: UserData) -> UserReadResponse:
        async with self.uow:
            user = await self.uow.user_repo.get_by_id(user_id)
            if not user:
                raise UserNotFoundError

            is_admin = acting_user.role == UserRole.ADMIN
            new_role = new_data.role if new_data.role is not None else user.role
            new_is_active = new_data.isActive if new_data.isActive is not None else user.is_active

            if not is_admin and (new_role != user.role or new_is_active != user.is_active):
                raise ForbiddenError

            was_active = user.is_active
            updated_user = await self.uow.user_repo.update(
                user_id, {"full_name": new_data.fullName, "role": new_role, "is_active": new_is_active}
            )

            if was_active and not new_is_active:
                await self.uow.refresh_token_repo.delete_all_for_user(user_id)

            return self._to_read_response(updated_user)

    async def deactivate_by_id(self, user_id: UUID) -> None:
        async with self.uow:
            user = await self.uow.user_repo.get_by_id(user_id)
            if not user:
                raise UserNotFoundError

            await self.uow.user_repo.deactivate(user_id, is_active=False, updated_at=datetime.now(UTC))
            await self.uow.refresh_token_repo.delete_all_for_user(user_id)
```

- [ ] **Step 9: Run the `UserService` tests — confirm they pass**

```bash
cd src && python -m pytest tests/test_user_service.py -v
```

Expected: 8 passed.

- [ ] **Step 10: Fix pagination defaults** — `app/core/utils/paginated.py`:

```python
from typing import Generic

from pydantic import BaseModel, Field

from app.core.custom_types import T


class PaginationParams(BaseModel):
    page: int = Field(0, ge=0, description="Page number")
    size: int = Field(20, ge=1, le=100, description="Page size")

    @property
    def offset(self) -> int:
        return self.page * self.size

    @property
    def limit(self) -> int:
        return self.size


class Page(BaseModel, Generic[T]):
    items: list[T]
    page: int
    size: int
    total: int

    @staticmethod
    def build(items: list[T], total: int, pagination: PaginationParams) -> "Page[T]":
        if len(items) > pagination.size:
            raise ValueError("items length exceeds pagination.size")

        return Page[T](items=items, page=pagination.page, size=pagination.size, total=total)
```

And `app/api/v1/dependencies/pagination.py`:

```python
from typing import Annotated

from fastapi import Depends, Query

from app.core.utils.paginated import PaginationParams


def get_pagination(
    page: int = Query(0, ge=0, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
) -> PaginationParams:
    return PaginationParams(page=page, size=size)


PaginationDep = Annotated[PaginationParams, Depends(get_pagination)]
```

- [ ] **Step 11: Create `app/api/v1/dependencies/user_filters.py`**

```python
from datetime import datetime
from typing import Annotated

from fastapi import Depends, Query

from app.core.enums import UserRole
from app.core.schemas.user import UserFilterQuery


def get_user_filters(
    email: str | None = Query(None),
    fullName: str | None = Query(None),
    role: UserRole | None = Query(None),
    isActive: bool | None = Query(None),
    createdFrom: datetime | None = Query(None),
    createdTo: datetime | None = Query(None),
) -> UserFilterQuery:
    return UserFilterQuery(
        email=email,
        fullName=fullName,
        role=role,
        isActive=isActive,
        createdFrom=createdFrom,
        createdTo=createdTo,
    )


UserFilterDep = Annotated[UserFilterQuery, Depends(get_user_filters)]
```

- [ ] **Step 12: Update `app/api/v1/dependencies/__init__.py`**

```python
from .current_user import AdminOrSelfDep, AdminUserDep, CurrentUserDep
from .pagination import PaginationDep
from .services import (
    AuthServiceDep,
    UserServiceDep,
)
from .session import SessionDep
from .user_filters import UserFilterDep
from .uow import UnitOfWorkDep

__all__ = [
    "AdminOrSelfDep",
    "AdminUserDep",
    "AuthServiceDep",
    "CurrentUserDep",
    "PaginationDep",
    "SessionDep",
    "UnitOfWorkDep",
    "UserFilterDep",
    "UserServiceDep",
]
```

- [ ] **Step 13: Rewrite `app/api/v1/endpoints/users.py`** — fixes the `{id}`/`user_id` path-param bug, wires `AdminOrSelfDep`, filters, and the new service methods:

```python
from uuid import UUID

from fastapi import APIRouter, status

from app.api.v1.dependencies import (
    AdminOrSelfDep,
    AdminUserDep,
    CurrentUserDep,
    PaginationDep,
    UserFilterDep,
    UserServiceDep,
)
from app.core.schemas.user import AdminRegisterUserBody, UserReadResponse, UserUpdateBody
from app.core.utils import Page

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=Page[UserReadResponse], status_code=status.HTTP_200_OK)
async def get_all(
    _: AdminUserDep,
    user_service: UserServiceDep,
    pagination: PaginationDep,
    filters: UserFilterDep,
) -> Page[UserReadResponse]:
    return await user_service.get_all_users(pagination, filters)


@router.post("", response_model=UserReadResponse, status_code=status.HTTP_201_CREATED)
async def create(_: AdminUserDep, user_service: UserServiceDep, user_data: AdminRegisterUserBody) -> UserReadResponse:
    return await user_service.create_user(user_data)


@router.get("/me", response_model=UserReadResponse, status_code=status.HTTP_200_OK)
async def get_me(user: CurrentUserDep, user_service: UserServiceDep) -> UserReadResponse:
    return await user_service.get_by_id(user.id)


@router.put("/me", response_model=UserReadResponse, status_code=status.HTTP_200_OK)
async def update_me(user: CurrentUserDep, user_service: UserServiceDep, new_data: UserUpdateBody) -> UserReadResponse:
    return await user_service.update_user(user.id, new_data, acting_user=user)


@router.get("/{user_id}", response_model=UserReadResponse, status_code=status.HTTP_200_OK)
async def get_by_id(_: AdminOrSelfDep, user_id: UUID, user_service: UserServiceDep) -> UserReadResponse:
    return await user_service.get_by_id(user_id)


@router.put("/{user_id}", response_model=UserReadResponse, status_code=status.HTTP_200_OK)
async def update_by_id(
    user: AdminOrSelfDep, user_id: UUID, user_service: UserServiceDep, new_data: UserUpdateBody
) -> UserReadResponse:
    return await user_service.update_user(user_id, new_data, acting_user=user)


@router.delete("/{user_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
async def deactivate_by_id(_: AdminUserDep, user_id: UUID, user_service: UserServiceDep) -> None:
    await user_service.deactivate_by_id(user_id)
```

- [ ] **Step 14: Add an `admin_headers` fixture to `src/tests/conftest.py`** — there's no public way to create the *first* admin yet (bootstrap-on-startup is Plan 3's scope), so tests that need an admin principal insert one directly against the test DB and mint a real access token for it:

Append to the existing `src/tests/conftest.py`:

```python
@pytest.fixture
async def admin_headers(db_session_factory, client):
    import uuid
    from datetime import UTC, datetime

    from app.core.enums import UserRole
    from app.infrastructure.models import User
    from app.services.jwt_service import JWTService

    admin_id = uuid.uuid4()
    now = datetime.now(UTC)
    async with db_session_factory() as session:
        session.add(
            User(
                id=admin_id,
                email="admin@fish.io",
                password=JWTService().get_password_hash("adminpass1"),
                full_name="Admin Fish",
                role=UserRole.ADMIN,
                is_active=True,
                created_by=admin_id,
                created_at=now,
                updated_at=now,
            )
        )
        await session.commit()

    access_token = JWTService().create_access_token(str(admin_id))
    return {"Authorization": f"Bearer {access_token}"}
```

(`admin_headers` depends on both `db_session_factory` and `client` so it writes to the exact same in-memory database `client`'s overridden dependency reads from.)

- [ ] **Step 15: Write the failing users-CRUD HTTP tests**

```python
# src/tests/test_users_endpoints.py
def _register(client, email="user@fish.io", password="password1", full_name="Test User"):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "fullName": full_name},
    )
    body = response.json()
    return body["user"]["id"], body["accessToken"]


def test_admin_can_create_user_with_arbitrary_role(client, admin_headers):
    response = client.post(
        "/api/v1/users",
        json={
            "email": "created@fish.io",
            "password": "password1",
            "fullName": "Created Fish",
            "role": "ADMIN",
            "isActive": True,
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    assert response.json()["role"] == "ADMIN"


def test_non_admin_cannot_create_user(client):
    _, access_token = _register(client)
    response = client.post(
        "/api/v1/users",
        json={"email": "x@fish.io", "password": "password1", "fullName": "X"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 403


def test_self_can_read_and_update_own_profile(client):
    user_id, access_token = _register(client, email="self@fish.io")
    headers = {"Authorization": f"Bearer {access_token}"}

    get_response = client.get(f"/api/v1/users/{user_id}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["email"] == "self@fish.io"

    put_response = client.put(f"/api/v1/users/{user_id}", json={"fullName": "Updated Name"}, headers=headers)
    assert put_response.status_code == 200
    assert put_response.json()["fullName"] == "Updated Name"


def test_me_endpoints_work_for_the_authenticated_user(client):
    _, access_token = _register(client, email="me@fish.io", full_name="Me Fish")
    headers = {"Authorization": f"Bearer {access_token}"}

    get_response = client.get("/api/v1/users/me", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["email"] == "me@fish.io"

    put_response = client.put("/api/v1/users/me", json={"fullName": "New Me"}, headers=headers)
    assert put_response.status_code == 200
    assert put_response.json()["fullName"] == "New Me"


def test_self_cannot_read_or_update_another_user(client):
    other_id, _ = _register(client, email="other@fish.io")
    _, my_token = _register(client, email="me2@fish.io")
    headers = {"Authorization": f"Bearer {my_token}"}

    get_response = client.get(f"/api/v1/users/{other_id}", headers=headers)
    assert get_response.status_code == 403

    put_response = client.put(f"/api/v1/users/{other_id}", json={"fullName": "Hacked Name"}, headers=headers)
    assert put_response.status_code == 403


def test_self_cannot_escalate_own_role(client):
    user_id, access_token = _register(client, email="escalate@fish.io")
    headers = {"Authorization": f"Bearer {access_token}"}

    response = client.put(
        f"/api/v1/users/{user_id}", json={"fullName": "Still Me", "role": "ADMIN"}, headers=headers
    )
    assert response.status_code == 403


def test_admin_can_change_role_and_is_active(client, admin_headers):
    user_id, _ = _register(client, email="promote@fish.io")

    response = client.put(
        f"/api/v1/users/{user_id}",
        json={"fullName": "Promoted Fish", "role": "ADMIN", "isActive": True},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["role"] == "ADMIN"


def test_admin_delete_soft_deactivates_and_revokes_refresh_tokens(client, admin_headers):
    user_id, _ = _register(client, email="delete@fish.io")
    refresh_cookie = client.cookies.get("refreshToken")

    delete_response = client.delete(f"/api/v1/users/{user_id}", headers=admin_headers)
    assert delete_response.status_code == 204

    get_response = client.get(f"/api/v1/users/{user_id}", headers=admin_headers)
    assert get_response.json()["isActive"] is False

    client.cookies.set("refreshToken", refresh_cookie)
    refresh_response = client.post("/api/v1/auth/refresh")
    assert refresh_response.status_code == 401


def test_admin_lists_users_with_pagination_and_filters(client, admin_headers):
    _register(client, email="alice@fish.io", full_name="Alice Fisher")
    _register(client, email="bob@fish.io", full_name="Bob Carp")

    response = client.get("/api/v1/users", params={"email": "alice"}, headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["email"] == "alice@fish.io"


def test_non_admin_cannot_list_users(client):
    _, access_token = _register(client)
    response = client.get("/api/v1/users", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 403
```

- [ ] **Step 16: Run it to confirm it fails**

```bash
cd src && python -m pytest tests/test_users_endpoints.py -v
```

Expected: failures — `/users/me` 500s (`get_current_by_id` doesn't exist), `/users/{id}` never binds `user_id` (404/422), `POST /users` uses the wrong body shape.

- [ ] **Step 17: Run the users-CRUD HTTP tests again — confirm they pass** (implementation was already written in Steps 3–13)

```bash
cd src && python -m pytest tests/test_users_endpoints.py -v
```

Expected: 10 passed.

- [ ] **Step 18: Run the full suite**

```bash
cd src && python -m pytest tests/ -v
```

Expected: every test from Plan 1, Task 1, Task 2, and this task passes — the whole plan is green end to end.

- [ ] **Step 19: Commit**

```bash
git add src/app/core/schemas/user.py src/app/core/utils/paginated.py \
  src/app/api/v1/dependencies/pagination.py src/app/api/v1/dependencies/user_filters.py \
  src/app/api/v1/dependencies/__init__.py src/app/infrastructure/repositories/user_repository.py \
  src/app/services/user_service.py src/app/api/v1/endpoints/users.py src/tests/conftest.py \
  src/tests/test_user_repository_filters.py src/tests/test_user_service.py src/tests/test_users_endpoints.py
git commit -m "feat: implement users CRUD with pagination, filters, RBAC, and ownership rules"
```

---

## Self-Review Notes

- **Spec coverage:** This plan covers spec stage 3 ("Auth-флоу: JWT access/refresh, refresh_tokens, ротация, cookie-хелпер, 4 эндпоинта") and stage 4 ("Users CRUD: пагинация, фильтры, RBAC/ownership, soft-delete") in full, cross-checked against the actual KotlinFish source (`AuthController.kt`, `UserController.kt`, `JWTService.kt`, `UserSpecifications.kt`, `Token.kt`) — not just the spec's prose summary — for exact endpoint shapes, claim names, filter semantics (`UserFilterQuery.createdFrom/createdTo` are `Instant`, i.e. full datetime range, confirmed against the Kotlin DTO), and response field names. Error-code taxonomy (stage 5) and observability/bootstrap (stage 6) are explicitly deferred to Plan 3, per the spec's own staging.
- **Pre-existing bugs fixed as part of this plan's scope:** the `/users/{id}` route declared a path param named `id` but its handler functions used `user_id`, so the value silently became a required *query* parameter instead of binding to the path (verified directly via `app.openapi()` before writing this plan) — fixed in Task 3 by renaming the route to `/{user_id}`. The public register flow previously reused `UserCreateBody` (which includes `role`/`isActive`), meaning a client could self-assign `role=ADMIN` on registration if that endpoint were ever wired up — fixed by giving register its own `UserRegisterBody` with no privilege fields, and hardcoding `role=USER, isActive=True` server-side in `AuthService.register`. `src/.env` (real secrets) was not gitignored — fixed in Task 1.
- **Known follow-ups for Plan 3:** error codes/`details` payloads (e.g. `EMAIL_ALREADY_EXISTS` instead of today's `CONFLICT`), the `X-Trace-Id` header/middleware, and admin bootstrap-on-startup remain as they were before this plan — this plan only wires functional behavior and correct status codes through the existing `DOMAIN_TO_API` map. `Token` (`app/core/schemas/token.py`) becomes fully dead code once this plan lands (superseded by `AccessTokenResponse`) — left in place rather than hunted down, since removing dead code that nothing imports is a trivial, low-value cleanup better bundled into Plan 3 or 4's own pass over these files.
- **Type consistency check:** `UserData` is the single "authenticated principal" type from Task 2 onward (`CurrentUserDep`, `AdminUserDep`, `AdminOrSelfDep`, `AuthService.verify_access_token`, `UserService.update_user`'s `acting_user` param) — no duplicate `TokenData`. `AuthService`/`UserService` both build `UserReadResponse` via an identically-shaped `_to_read_response` static method (kept duplicated per-service rather than extracted, since each service's only shared dependency would be the mapping function itself — YAGNI). `UserRepository.get_filtered`/`count_filtered` take the same `UserFilterQuery` object `UserService.get_all_users` receives from `UserFilterDep` — no shape mismatch. `AccessTokenResponse`/`UserAndAccessTokenResponse` field names (`accessToken`, `expiresIn`) are consistent between `token.py`, `auth_service.py`, and `auth.py`'s response models.
