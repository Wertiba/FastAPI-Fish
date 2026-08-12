# FastAPI-Fish Stage 3: Contract & Observability Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining API-contract and observability gaps between `FastAPI-Fish` and the reference `KotlinFish` template: clean up leftover foreign-domain code, fix error-response/validation details, add a real `X-Trace-Id` middleware, make CORS and admin bootstrap environment-driven like the Kotlin version, and add a Prometheus metrics endpoint plus Kotlin-shaped health paths.

**Architecture:** No structural changes — same `api -> services -> unit_of_work -> repositories -> models` layering. This stage only touches: `app/core/exceptions`, `app/api/v1/exceptions`, `app/core/schemas`, `app/main.py`, `app/api/v1/endpoints/health.py` (split into `health.py` + new `metrics.py`), and a new `app/core/middleware/trace_id.py`.

**Tech Stack:** FastAPI, Starlette `BaseHTTPMiddleware`, Pydantic v2, Dynaconf, `prometheus-client` (new dependency), pytest + `TestClient` (existing in-memory SQLite fixtures in `src/tests/conftest.py`).

## Global Constraints

- Base path stays `/api/v1` (unchanged).
- All response field names stay camelCase; all new/changed user-facing error and validation text is in **English** (per the project's own design doc, `docs/superpowers/specs/2026-08-08-fastapi-fish-parity-design.md`).
- Error codes and behavior must match the table in that design doc exactly: `EMAIL_ALREADY_EXISTS` (409), `NOT_FOUND` (404), `UNAUTHORIZED` (401), `FORBIDDEN` (403), `USER_INACTIVE` (423), `VALIDATION_FAILED` (422).
- Every task must leave `pytest` (run from `src/`) fully green before moving to the next task — this repo has no CI yet (that lands in a later stage), so this plan is the only safety net.
- Don't touch `app/infrastructure/*`, `app/services/user_service.py` business logic, or the DB schema — this stage is contract/observability only.
- Run tests with: `cd src && python -m pytest` (needs a populated `src/.env` copied from `src/.env.example`; no live Postgres required — the suite runs on in-memory SQLite).

---

### Task 1: Remove leftover foreign-domain exception (`DeficiencyApproversError`)

The project's own design doc (`docs/superpowers/specs/2026-08-08-fastapi-fish-parity-design.md`, section "Ошибки и валидация") explicitly says `DeficiencyApproversError` and friends are leftovers from an unrelated past project and must be deleted from `exc_map.py`. It's still there in both `user_exs.py` and `exc_map.py`.

**Files:**
- Modify: `src/app/core/exceptions/user_exs.py`
- Modify: `src/app/api/v1/exceptions/exc_map.py`
- Test: `src/tests/test_repo_hygiene.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: nothing new — this is pure deletion. Later tasks must not reintroduce `DeficiencyApproversError`.

- [ ] **Step 1: Write the failing test**

Add to `src/tests/test_repo_hygiene.py`:

```python
def test_exc_map_has_no_foreign_domain_leftovers():
    text = (REPO_ROOT / "src" / "app" / "api" / "v1" / "exceptions" / "exc_map.py").read_text(encoding="utf-8")
    assert "DeficiencyApprovers" not in text


def test_user_exs_has_no_foreign_domain_leftovers():
    text = (REPO_ROOT / "src" / "app" / "core" / "exceptions" / "user_exs.py").read_text(encoding="utf-8")
    assert "DeficiencyApprovers" not in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src && python -m pytest tests/test_repo_hygiene.py -v`
Expected: FAIL on both new tests (`DeficiencyApprovers` is present in both files).

- [ ] **Step 3: Delete the leftover code**

In `src/app/core/exceptions/user_exs.py`, remove the class:

```python
class DeficiencyApproversError(EntityError):
    pass
```

In `src/app/api/v1/exceptions/exc_map.py`, remove the `DeficiencyApproversError` import from `app.core.exceptions.user_exs` and remove this entry from `DOMAIN_TO_API`:

```python
    DeficiencyApproversError: lambda path, exc=None: ValidationFailed(
        path=path,
        message="Invalid number of approvers"
    ),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src && python -m pytest tests/test_repo_hygiene.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite to check for regressions**

Run: `cd src && python -m pytest -v`
Expected: all PASS (nothing else references `DeficiencyApproversError`).

- [ ] **Step 6: Commit**

```bash
git add src/app/core/exceptions/user_exs.py src/app/api/v1/exceptions/exc_map.py src/tests/test_repo_hygiene.py
git commit -m "chore: remove leftover DeficiencyApproversError from foreign domain"
```

---

### Task 2: `EMAIL_ALREADY_EXISTS` error code with `details`

The design doc's error table requires code `EMAIL_ALREADY_EXISTS` (not a generic `CONFLICT`) with `details: {field: "email", value}` on duplicate-email registration/creation. Today `UserAlreadyExistsError` maps to a generic `Conflict` (`code="CONFLICT"`) with no `details`.

**Files:**
- Modify: `src/app/api/v1/exceptions/api_exs.py`
- Modify: `src/app/core/exceptions/user_exs.py`
- Modify: `src/app/api/v1/exceptions/exc_map.py`
- Modify: `src/app/services/auth_service.py`
- Modify: `src/app/services/user_service.py`
- Test: `src/tests/test_auth_endpoints.py`, `src/tests/test_users_endpoints.py`

**Interfaces:**
- Consumes: `EntityError` base class from `app.core.exceptions.base` (unchanged).
- Produces: `UserAlreadyExistsError(email: str)` (was previously raised with no args) — any other code path raising it must now pass `email=`.

- [ ] **Step 1: Write the failing test**

Update the existing test in `src/tests/test_auth_endpoints.py`:

```python
def test_register_rejects_duplicate_email(client):
    payload = {"email": "dup@fish.io", "password": "password1", "fullName": "Fish"}
    client.post("/api/v1/auth/register", json=payload)
    response = client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "EMAIL_ALREADY_EXISTS"
    assert body["details"] == {"field": "email", "value": "dup@fish.io"}
```

Add to `src/tests/test_users_endpoints.py` (reuse whatever admin-auth fixture the file already uses, e.g. `admin_headers`):

```python
def test_create_user_rejects_duplicate_email_with_details(client, admin_headers):
    payload = {"email": "dup2@fish.io", "password": "password1", "fullName": "Fish Two"}
    client.post("/api/v1/users", json=payload, headers=admin_headers)
    response = client.post("/api/v1/users", json=payload, headers=admin_headers)

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "EMAIL_ALREADY_EXISTS"
    assert body["details"] == {"field": "email", "value": "dup2@fish.io"}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd src && python -m pytest tests/test_auth_endpoints.py::test_register_rejects_duplicate_email tests/test_users_endpoints.py::test_create_user_rejects_duplicate_email_with_details -v`
Expected: FAIL — current body has `code == "CONFLICT"` and no `details`.

- [ ] **Step 3: Give `UserAlreadyExistsError` an `email` field**

In `src/app/core/exceptions/user_exs.py`, replace:

```python
class UserAlreadyExistsError(EntityError):
    pass
```

with:

```python
class UserAlreadyExistsError(EntityError):
    def __init__(self, email: str):
        super().__init__(email)
        self.email = email
```

- [ ] **Step 4: Add `EmailAlreadyExists` API exception, drop the generic `Conflict`**

In `src/app/api/v1/exceptions/api_exs.py`, replace:

```python
class Conflict(APIException):
    status_code = status.HTTP_409_CONFLICT
    code = "CONFLICT"
    message = "Data conflict"
```

with:

```python
class EmailAlreadyExists(APIException):
    status_code = status.HTTP_409_CONFLICT
    code = "EMAIL_ALREADY_EXISTS"
    message = "User with this email already exists"
```

(`Conflict` has no other callers — confirm with `grep -rn "Conflict" src/app` before deleting; if something else still imports it, keep both classes instead of replacing.)

- [ ] **Step 5: Wire the new exception with `details` in `exc_map.py`**

In `src/app/api/v1/exceptions/exc_map.py`, update the import (`Conflict` -> `EmailAlreadyExists`) and replace:

```python
    UserAlreadyExistsError: lambda path, exc=None: Conflict(
        path=path,
        message="User already exists",
    ),
```

with:

```python
    UserAlreadyExistsError: lambda path, exc: EmailAlreadyExists(
        path=path,
        details={"field": "email", "value": exc.email},
    ),
```

- [ ] **Step 6: Pass `email=` at every raise site**

In `src/app/services/auth_service.py`, in `register()`:

```python
            existing_user = await self.uow.user_repo.get_by_email(user_data.email)
            if existing_user:
                raise UserAlreadyExistsError(email=user_data.email)
```

and:

```python
            except DuplicateError:
                raise UserAlreadyExistsError(email=user_data.email) from None
```

In `src/app/services/user_service.py`, in `create_user()`:

```python
            existing = await self.uow.user_repo.get_by_email(data.email)
            if existing:
                raise UserAlreadyExistsError(email=data.email)
```

and:

```python
            except DuplicateError:
                raise UserAlreadyExistsError(email=data.email) from None
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd src && python -m pytest tests/test_auth_endpoints.py tests/test_users_endpoints.py -v`
Expected: PASS.

- [ ] **Step 8: Run the full suite**

Run: `cd src && python -m pytest -v`
Expected: all PASS.

- [ ] **Step 9: Commit**

```bash
git add src/app/api/v1/exceptions/api_exs.py src/app/api/v1/exceptions/exc_map.py src/app/core/exceptions/user_exs.py src/app/services/auth_service.py src/app/services/user_service.py src/tests/test_auth_endpoints.py src/tests/test_users_endpoints.py
git commit -m "fix: EMAIL_ALREADY_EXISTS error code with field/value details"
```

---

### Task 3: `fullName` regex validation (1:1 with `UserConstraints.kt`)

The design doc specifies `fullName` must match `^[а-яА-Яa-zA-Z0-9 _-]{2,200}$`. Today it only enforces `min_length=2, max_length=200` with no character-set check.

**Files:**
- Modify: `src/app/core/schemas/user.py`
- Test: `src/tests/test_auth_endpoints.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: nothing new — pure validation tightening on `UserRegisterBody.fullName` and `UserUpdateBody.fullName` (`AdminRegisterUserBody` inherits from `UserRegisterBody`, so it's covered too).

- [ ] **Step 1: Write the failing test**

Add to `src/tests/test_auth_endpoints.py`:

```python
def test_register_rejects_full_name_with_invalid_characters(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "badname@fish.io", "password": "password1", "fullName": "Fish!!!"},
    )
    assert response.status_code == 422


def test_register_accepts_cyrillic_full_name(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "cyrillic@fish.io", "password": "password1", "fullName": "Иван Иванов"},
    )
    assert response.status_code == 201
```

- [ ] **Step 2: Run tests to verify the first one fails**

Run: `cd src && python -m pytest tests/test_auth_endpoints.py::test_register_rejects_full_name_with_invalid_characters -v`
Expected: FAIL (currently `"Fish!!!"` passes validation and returns 201).

- [ ] **Step 3: Add the regex**

In `src/app/core/schemas/user.py`, replace both occurrences of:

```python
    fullName: Annotated[str, Field(min_length=2, max_length=200)]
```

(one in `UserRegisterBody`, one in `UserUpdateBody`) with:

```python
    fullName: Annotated[str, Field(pattern=r"^[а-яА-Яa-zA-Z0-9 _-]{2,200}$")]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd src && python -m pytest tests/test_auth_endpoints.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `cd src && python -m pytest -v`
Expected: all PASS (double-check no existing fixture uses a `fullName` value outside this charset, e.g. em-dashes or accented Latin letters — grep `fullName.*=` across `src/tests` if anything fails).

- [ ] **Step 6: Commit**

```bash
git add src/app/core/schemas/user.py src/tests/test_auth_endpoints.py
git commit -m "fix: enforce fullName charset regex matching Kotlin UserConstraints"
```

---

### Task 4: English validation error message

`ValidationErrorResponse.message` defaults to Russian (`"Некоторые поля не прошли валидацию"`). The design doc requires English error/validation text throughout, matching the Kotlin version.

**Files:**
- Modify: `src/app/core/schemas/responses.py`
- Test: `src/tests/test_auth_endpoints.py`

- [ ] **Step 1: Write the failing test**

Add to `src/tests/test_auth_endpoints.py`:

```python
def test_validation_error_message_is_english(client):
    response = client.post("/api/v1/auth/register", json={"email": "not-an-email", "password": "x", "fullName": ""})
    assert response.status_code == 422
    assert response.json()["message"] == "Some fields are not correct."
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src && python -m pytest tests/test_auth_endpoints.py::test_validation_error_message_is_english -v`
Expected: FAIL — current message is the Russian default.

- [ ] **Step 3: Fix the default**

In `src/app/core/schemas/responses.py`, in `ValidationErrorResponse`, replace:

```python
    message: str = "Некоторые поля не прошли валидацию"
```

with:

```python
    message: str = "Some fields are not correct."
```

(This matches the existing `ValidationFailed.message` in `app/api/v1/exceptions/api_exs.py`, so both validation paths now say the same thing in English.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src && python -m pytest tests/test_auth_endpoints.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/app/core/schemas/responses.py src/tests/test_auth_endpoints.py
git commit -m "fix: use English default message for validation errors"
```

---

### Task 5: `X-Trace-Id` middleware on every response

Today trace IDs are generated ad hoc per error handler (and the validation handler reads the wrong header, `X-Request-Id`, instead of `X-Trace-Id`). Nothing sets the header on successful responses. The design doc requires: middleware reads the request's `X-Trace-Id` (or generates a `uuid4`), stashes it in a contextvar, stamps it on **every** response, and error bodies embed the same value as `traceId`.

**Files:**
- Create: `src/app/core/middleware/__init__.py`
- Create: `src/app/core/middleware/trace_id.py`
- Modify: `src/app/main.py`
- Modify: `src/app/api/v1/exceptions/base.py`
- Modify: `src/app/api/v1/exceptions/handlers.py`
- Test: `src/tests/test_cookies.py` or a new `src/tests/test_trace_id.py` (create the latter — cleaner)

**Interfaces:**
- Produces: `get_trace_id() -> str` in `app.core.middleware.trace_id`, returns `""` outside a request context, else the current request's trace id. `TraceIdMiddleware` (Starlette `BaseHTTPMiddleware` subclass), header name `TRACE_ID_HEADER = "X-Trace-Id"`.
- Consumes (later tasks): `app.api.v1.exceptions.base.APIException` now falls back to `get_trace_id()` instead of always minting a fresh `uuid4`.

- [ ] **Step 1: Write the failing tests**

Create `src/tests/test_trace_id.py`:

```python
def test_response_always_includes_trace_id_header(client):
    response = client.get("/api/v1/ping")
    assert "x-trace-id" in {k.lower() for k in response.headers}


def test_trace_id_header_is_echoed_back_when_provided(client):
    response = client.get("/api/v1/ping", headers={"X-Trace-Id": "fixed-trace-1"})
    assert response.headers["x-trace-id"] == "fixed-trace-1"


def test_error_response_trace_id_matches_request_header(client):
    response = client.get("/api/v1/users/me", headers={"X-Trace-Id": "fixed-trace-2"})
    assert response.status_code == 401
    assert response.headers["x-trace-id"] == "fixed-trace-2"
    assert response.json()["traceId"] == "fixed-trace-2"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd src && python -m pytest tests/test_trace_id.py -v`
Expected: FAIL — no `x-trace-id` header exists today, and the 401 body's `traceId` is a random, unrelated uuid4.

- [ ] **Step 3: Create the middleware**

Create `src/app/core/middleware/__init__.py` (empty file, makes it a package).

Create `src/app/core/middleware/trace_id.py`:

```python
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

TRACE_ID_HEADER = "X-Trace-Id"

_trace_id_ctx: ContextVar[str] = ContextVar("trace_id", default="")


def get_trace_id() -> str:
    return _trace_id_ctx.get()


class TraceIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        trace_id = request.headers.get(TRACE_ID_HEADER) or str(uuid.uuid4())
        token = _trace_id_ctx.set(trace_id)
        try:
            response = await call_next(request)
        finally:
            _trace_id_ctx.reset(token)
        response.headers[TRACE_ID_HEADER] = trace_id
        return response
```

- [ ] **Step 4: Wire the middleware into `main.py`**

In `src/app/main.py`, add the import:

```python
from app.core.middleware.trace_id import TraceIdMiddleware
```

and add, after the existing `app.add_middleware(CORSMiddleware, ...)` call:

```python
app.add_middleware(TraceIdMiddleware)
```

- [ ] **Step 5: Make `APIException` fall back to the contextvar**

In `src/app/api/v1/exceptions/base.py`, add the import:

```python
from app.core.middleware.trace_id import get_trace_id
```

and change:

```python
        self.trace_id = trace_id or str(uuid4())
```

to:

```python
        self.trace_id = trace_id or get_trace_id() or str(uuid4())
```

- [ ] **Step 6: Fix the validation handler to use the same trace id**

In `src/app/api/v1/exceptions/handlers.py`, replace the import of `uuid4` with an import of `get_trace_id`:

```python
from app.core.middleware.trace_id import get_trace_id
```

(drop the now-unused `from uuid import UUID, uuid4` import if nothing else in the file needs `UUID`/`uuid4` — check first.)

Replace:

```python
        trace_id = request.headers.get("X-Request-Id") or str(uuid4())
```

with:

```python
        trace_id = get_trace_id()
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `cd src && python -m pytest tests/test_trace_id.py -v`
Expected: PASS.

- [ ] **Step 8: Run the full suite**

Run: `cd src && python -m pytest -v`
Expected: all PASS.

- [ ] **Step 9: Commit**

```bash
git add src/app/core/middleware src/app/main.py src/app/api/v1/exceptions/base.py src/app/api/v1/exceptions/handlers.py src/tests/test_trace_id.py
git commit -m "feat: X-Trace-Id middleware stamped on every response"
```

---

### Task 6: CORS origins from `APP_CORS_ALLOWED_ORIGINS`

CORS origins are hardcoded in `main.py`. The design doc lists `APP_CORS_ALLOWED_ORIGINS` (CSV) as the env var, matching Kotlin.

**Files:**
- Modify: `src/app/main.py`
- Modify: `src/.env.example`
- Test: `src/tests/test_trace_id.py` (or a new small test file — reuse `test_trace_id.py` for convenience since it already hits `/api/v1/ping`)

- [ ] **Step 1: Write the failing tests**

Add to `src/tests/test_trace_id.py`:

```python
def test_cors_allows_configured_origin(client):
    response = client.get("/api/v1/ping", headers={"Origin": "http://localhost"})
    assert response.headers.get("access-control-allow-origin") == "http://localhost"


def test_cors_rejects_unconfigured_origin(client):
    response = client.get("/api/v1/ping", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in {k.lower() for k in response.headers}
```

- [ ] **Step 2: Run tests**

Run: `cd src && python -m pytest tests/test_trace_id.py::test_cors_allows_configured_origin tests/test_trace_id.py::test_cors_rejects_unconfigured_origin -v`
Expected: PASS already, since the hardcoded list happens to include `http://localhost` — this step is here to lock in current behavior *before* the refactor, so a mistake in Step 3 shows up as a new failure, not a silent regression.

- [ ] **Step 3: Read origins from settings**

In `src/app/main.py`, replace:

```python
origins = [
    "http://localhost",
    "http://localhost:8080",
]
```

with:

```python
from app.core.config import settings

_DEFAULT_CORS_ORIGINS = "http://localhost,http://localhost:8080"
origins = [
    origin.strip()
    for origin in settings.get("APP_CORS_ALLOWED_ORIGINS", _DEFAULT_CORS_ORIGINS).split(",")
    if origin.strip()
]
```

(Add the `from app.core.config import settings` import near the top with the other imports — `main.py` doesn't import `settings` yet.)

- [ ] **Step 4: Document the new variable**

In `src/.env.example`, add near `APP_COOKIE_SECURE`:

```
# Comma-separated list of origins allowed by CORS. Defaults to localhost if unset.
APP_CORS_ALLOWED_ORIGINS=http://localhost,http://localhost:8080
```

- [ ] **Step 5: Run tests to verify they still pass**

Run: `cd src && python -m pytest tests/test_trace_id.py -v`
Expected: PASS (behavior unchanged by default; now overridable via env).

- [ ] **Step 6: Run the full suite**

Run: `cd src && python -m pytest -v`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add src/app/main.py src/.env.example src/tests/test_trace_id.py
git commit -m "feat: drive CORS allowed origins from APP_CORS_ALLOWED_ORIGINS"
```

---

### Task 7: Admin bootstrap on every startup (FastAPI `lifespan`)

Today admin creation is a manual script (`python -m app.actions.run`), never invoked automatically. Kotlin's `AdminInitializer` (`ApplicationRunner`) runs on every boot. This task wires the existing, already-idempotent `create_admin()` into FastAPI's `lifespan`, and renames the admin env vars to the `APP_ADMIN_*` names the design doc specifies (currently `ADMIN_EMAIL`/`ADMIN_PASSWORD`/`ADMIN_FULLNAME`, no `APP_` prefix — inconsistent with every other `APP_*` setting in this project).

**Files:**
- Modify: `src/app/main.py`
- Modify: `src/app/actions/first_admin.py`
- Modify: `src/.env.example`
- Modify: `src/tests/conftest.py`
- Test: `src/tests/test_app_boot.py`

**Interfaces:**
- Consumes: `create_admin(session: AsyncSession)` from `app.actions.first_admin` (unchanged signature).
- Produces: nothing new for other tasks.

**Why `conftest.py` needs a change:** the `client` fixture overrides `db_helper.session_getter` via `app.dependency_overrides`, which only affects FastAPI's `Depends()` resolution. The new `lifespan` hook calls `db_helper.session_factory()` directly (same as the existing manual `actions/run.py` script does) — outside of FastAPI's DI — so it would otherwise try to open a real Postgres connection during every test. The fixture must also monkeypatch the `db_helper.session_factory` attribute itself for the duration of the test.

- [ ] **Step 1: Write the failing test**

Add to `src/tests/test_app_boot.py`:

```python
async def test_admin_bootstrap_runs_on_startup(client, db_session_factory):
    from sqlalchemy import select

    from app.core.config import settings
    from app.infrastructure.models import User

    async with db_session_factory() as session:
        result = await session.execute(select(User).where(User.email == settings.APP_ADMIN_EMAIL))
        admin = result.scalar_one_or_none()

    assert admin is not None
    assert admin.role == "ADMIN"
```

(This depends on both `client` and `db_session_factory` fixtures already defined in `src/tests/conftest.py` — `client` triggers app startup, `db_session_factory` gives direct access to the same in-memory SQLite the app used.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src && python -m pytest tests/test_app_boot.py::test_admin_bootstrap_runs_on_startup -v`
Expected: FAIL — no admin row exists because nothing calls `create_admin` on startup, and `settings.APP_ADMIN_EMAIL` doesn't exist yet either (still `settings.ADMIN_EMAIL`).

- [ ] **Step 3: Rename the env vars**

In `src/.env.example`, replace:

```
ADMIN_EMAIL=admin@example.com
ADMIN_FULLNAME='Admin Admin'
ADMIN_PASSWORD=change-me-please
```

with:

```
APP_ADMIN_EMAIL=admin@example.com
APP_ADMIN_FULLNAME='Admin Admin'
APP_ADMIN_PASSWORD=change-me-please
```

In `src/app/actions/first_admin.py`, replace:

```python
    email = settings.ADMIN_EMAIL
```

with:

```python
    email = settings.APP_ADMIN_EMAIL
```

and replace:

```python
        password=argon2.hash(settings.ADMIN_PASSWORD),
        full_name=settings.ADMIN_FULLNAME,
```

with:

```python
        password=argon2.hash(settings.APP_ADMIN_PASSWORD),
        full_name=settings.APP_ADMIN_FULLNAME,
```

- [ ] **Step 4: Update your local `.env`**

`src/.env` is git-ignored and not touched by this plan — manually rename the three keys in your own `src/.env` to `APP_ADMIN_EMAIL`/`APP_ADMIN_PASSWORD`/`APP_ADMIN_FULLNAME` so `pytest` and local runs keep working (the plan's `.env.example` change above is the template; existing local `.env` files must be updated by hand once, per developer).

- [ ] **Step 5: Patch `conftest.py`'s `client` fixture**

In `src/tests/conftest.py`, replace:

```python
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

with:

```python
@pytest.fixture
async def client(db_session_factory):
    async def override_session_getter():
        async with db_session_factory() as session:
            yield session

    app.dependency_overrides[db_helper.session_getter] = override_session_getter
    original_session_factory = db_helper.session_factory
    db_helper.session_factory = db_session_factory

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        db_helper.session_factory = original_session_factory
        app.dependency_overrides.clear()
```

- [ ] **Step 6: Add the `lifespan` hook to `main.py`**

In `src/app/main.py`, add imports:

```python
from contextlib import asynccontextmanager

from app.actions.first_admin import create_admin
from app.infrastructure.database.db_helper import db_helper
```

Replace:

```python
app = FastAPI()
```

with:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with db_helper.session_factory() as session:
        await create_admin(session)
    yield


app = FastAPI(lifespan=lifespan)
```

- [ ] **Step 7: Remove the now-redundant manual bootstrap from `entrypoint.sh`**

`src/entrypoint.sh` currently runs `python -m app.actions.run` (the manual bootstrap script) before starting the app. With `lifespan` now doing this on every boot, that line is dead weight — remove it. Replace:

```sh
echo "[entrypoint] Creating first admin if not exists..."
python -m app.actions.run

echo "[entrypoint] Starting application..."
exec "$@"
```

with:

```sh
echo "[entrypoint] Starting application..."
exec "$@"
```

(`app/actions/run.py` and `app/actions/first_admin.py` stay — `first_admin.py`'s `create_admin()` is now called from `main.py`'s `lifespan`, and `run.py` remains available as a standalone manual-reseed tool if ever needed outside the app process.)

- [ ] **Step 8: Run test to verify it passes**

Run: `cd src && python -m pytest tests/test_app_boot.py -v`
Expected: PASS.

- [ ] **Step 9: Run the full suite**

Run: `cd src && python -m pytest -v`
Expected: all PASS (every test using the `client` fixture now also boots the admin user once per test — harmless, `create_admin` is idempotent and scoped to its own in-memory DB per test).

- [ ] **Step 10: Commit**

```bash
git add src/app/main.py src/app/actions/first_admin.py src/.env.example src/tests/conftest.py src/tests/test_app_boot.py src/entrypoint.sh
git commit -m "feat: bootstrap admin user automatically on startup via lifespan"
```

---

### Task 8: Prometheus metrics endpoint

Kotlin exposes `/actuator/prometheus` via Micrometer. The design doc's "не цели" section says an exact Actuator clone isn't required — a functional equivalent is enough: `GET /api/v1/metrics` in Prometheus exposition format.

**Files:**
- Modify: `src/requirements.txt`
- Create: `src/app/api/v1/endpoints/metrics.py`
- Modify: `src/app/api/v1/endpoints/__init__.py`
- Test: `src/tests/test_app_boot.py`

- [ ] **Step 1: Write the failing test**

Add to `src/tests/test_app_boot.py`:

```python
def test_metrics_endpoint_exposes_prometheus_format(client):
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")
    assert "# HELP" in response.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src && python -m pytest tests/test_app_boot.py::test_metrics_endpoint_exposes_prometheus_format -v`
Expected: FAIL with 404 (no `/api/v1/metrics` route exists).

- [ ] **Step 3: Add the dependency**

Add to `src/requirements.txt` (keep alphabetical, next to `pluggy`/`pycparser`):

```
prometheus_client==0.21.1
```

Install it: `cd src && pip install prometheus_client==0.21.1`

- [ ] **Step 4: Create the endpoint**

Create `src/app/api/v1/endpoints/metrics.py`:

```python
from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

router = APIRouter(prefix="", tags=["Metrics"])


@router.get("/metrics")
async def metrics() -> Response:
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
```

- [ ] **Step 5: Register the router**

In `src/app/api/v1/endpoints/__init__.py`, add the import and registration (file currently is):

```python
from fastapi import APIRouter

from .auth import router as auth_router
from .health import router as ping_router
from .users import router as user_router

router = APIRouter(prefix="/v1")

router.include_router(ping_router)
router.include_router(auth_router)
router.include_router(user_router)
```

Change to:

```python
from fastapi import APIRouter

from .auth import router as auth_router
from .health import router as ping_router
from .metrics import router as metrics_router
from .users import router as user_router

router = APIRouter(prefix="/v1")

router.include_router(ping_router)
router.include_router(metrics_router)
router.include_router(auth_router)
router.include_router(user_router)
```

- [ ] **Step 6: Run test to verify it passes**

Run: `cd src && python -m pytest tests/test_app_boot.py -v`
Expected: PASS.

- [ ] **Step 7: Run the full suite**

Run: `cd src && python -m pytest -v`
Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
git add src/requirements.txt src/app/api/v1/endpoints/metrics.py src/app/api/v1/endpoints/__init__.py src/tests/test_app_boot.py
git commit -m "feat: expose Prometheus metrics at /api/v1/metrics"
```

---

### Task 9: Rename health endpoints to `/health/liveness` and `/health/readiness`

The design doc's Observability section specifies `GET /api/v1/health/liveness` and `GET /api/v1/health/readiness`. Today the paths are `/ping`, `/health`, `/ready` — functionally close but not contract-matching, and there's a redundant plain `/health` alongside `/ready`.

**Files:**
- Modify: `src/app/api/v1/endpoints/health.py`
- Modify: `src/app/api/v1/endpoints/__init__.py`
- Modify: `src/tests/test_app_boot.py`
- Modify: `src/tests/test_trace_id.py`
- Modify: `docker-compose.yml`

**Interfaces:**
- Produces: `GET /api/v1/health/liveness` (always 200), `GET /api/v1/health/readiness` (200 or 503 with `checks`). The old `/ping`, `/health`, `/ready` paths are removed — this is a breaking rename, not an addition.

- [ ] **Step 1: Update the tests first (red)**

In `src/tests/test_app_boot.py`, replace:

```python
def test_app_imports_and_ping_responds():
    client = TestClient(app)
    response = client.get("/api/v1/ping")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

with:

```python
def test_app_imports_and_liveness_responds():
    client = TestClient(app)
    response = client.get("/api/v1/health/liveness")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

In `src/tests/test_trace_id.py`, replace every `"/api/v1/ping"` with `"/api/v1/health/liveness"` (three occurrences from Tasks 5 and 6).

In `src/tests/test_app_boot.py`, also update the metrics test from Task 8 if it references `/api/v1/ping` anywhere (it doesn't — leave as is).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd src && python -m pytest tests/test_app_boot.py tests/test_trace_id.py -v`
Expected: FAIL with 404s (`/api/v1/health/liveness` doesn't exist yet).

- [ ] **Step 3: Rewrite `health.py`**

Replace the full contents of `src/app/api/v1/endpoints/health.py` with:

```python
from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.core.schemas.responses import PingResponse
from app.infrastructure.database.db_helper import db_helper

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("/liveness", response_model=PingResponse, status_code=status.HTTP_200_OK)
async def liveness() -> PingResponse:
    return PingResponse(status="ok")


@router.get("/readiness", status_code=status.HTTP_200_OK)
async def readiness(response: Response) -> dict:
    checks = {}
    try:
        async for session in db_helper.session_getter():
            await session.execute(text("SELECT 1"))
            checks["database"] = "ready"
            break
    except Exception as e:
        checks["database"] = f"not ready: {e}"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "not ready", "checks": checks}

    return {"status": "ready", "checks": checks}
```

- [ ] **Step 4: Update the router import alias**

In `src/app/api/v1/endpoints/__init__.py`, the import `from .health import router as ping_router` still works (the module still exports `router`) but the name is now misleading. Rename it for clarity:

```python
from fastapi import APIRouter

from .auth import router as auth_router
from .health import router as health_router
from .metrics import router as metrics_router
from .users import router as user_router

router = APIRouter(prefix="/v1")

router.include_router(health_router)
router.include_router(metrics_router)
router.include_router(auth_router)
router.include_router(user_router)
```

- [ ] **Step 5: Update the Docker healthcheck**

In `docker-compose.yml`, replace:

```yaml
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:8080/api/v1/ping"]
```

with:

```yaml
    healthcheck:
      test: ["CMD", "curl", "-fsS", "http://localhost:8080/api/v1/health/liveness"]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd src && python -m pytest tests/test_app_boot.py tests/test_trace_id.py -v`
Expected: PASS.

- [ ] **Step 7: Run the full suite**

Run: `cd src && python -m pytest -v`
Expected: all PASS. Also grep the whole repo for any remaining `/api/v1/ping` references (`grep -rn "api/v1/ping" .` from repo root) — fix any stragglers in docs or scripts.

- [ ] **Step 8: Commit**

```bash
git add src/app/api/v1/endpoints/health.py src/app/api/v1/endpoints/__init__.py src/tests/test_app_boot.py src/tests/test_trace_id.py docker-compose.yml
git commit -m "feat: rename health endpoints to /health/liveness and /health/readiness"
```

---

## After this plan

Two more stages remain to fully match `KotlinFish`'s forkability, tracked as separate plans:

- **Stage 4 — Templating & forkability**: write `src/README.md` (currently empty), add `actions/init-project.sh`/`.ps1` rename scripts, add an OpenAPI export script producing `docs/api-docs.json`.
- **Stage 5 — Tests & CI**: add real-Postgres integration tests (the current suite runs on in-memory SQLite only) and a `.github/workflows/ci.yml` running `ruff check` + `pytest`.

Stage 4 can be done independently of Stage 5. Both should be done after this plan, since Stage 4's README documents the final env var names (`APP_ADMIN_EMAIL`, `APP_CORS_ALLOWED_ORIGINS`, health/metrics paths) this plan introduces.
