# FastAPI-Fish Stage 1: Boot & Data Layer — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make FastAPI-Fish import and boot cleanly, and replace its data layer (models, repositories, unit of work, Alembic migration) with a SQLAlchemy 2.0 declarative schema that is a 1:1 match of KotlinFish's `V1__init.sql`.

**Architecture:** This is the first of four plans bringing FastAPI-Fish to parity with KotlinFish (see `docs/superpowers/specs/2026-08-08-fastapi-fish-parity-design.md`). The spec's 8 stages are grouped into 4 plans: **Plan 1 (this plan)** = spec stages 1+2 (cleanup, boot fix, DB model/migration). Plan 2 = spec stages 3+4 (auth flow, users CRUD contract). Plan 3 = spec stages 5+6 (errors/validation, observability). Plan 4 = spec stages 7+8 (templating, tests/CI). This plan deliberately does **not** rewrite the auth/users API contract (endpoints keep today's behavior) — it only makes the app boot and gives it a correct, migrated persistence layer to build on.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 (async, declarative), Alembic, asyncpg, Pydantic v2, Dynaconf, pytest.

## Global Constraints

- Target DB schema is the exact DDL from the spec (`users`, `refresh_tokens` — see Task 4) via one Alembic migration. No deviation from column names, types, or constraints.
- Models (`app/infrastructure/models/`) are plain SQLAlchemy 2.0 declarative classes (`DeclarativeBase`, `Mapped`, `mapped_column`) — **no SQLModel**. SQLModel is fully removed from the codebase and from `src/requirements.txt` by the end of this plan.
- The auth/users API contract (endpoints, request/response schemas, RBAC) is explicitly **out of scope** for this plan and is deferred to Plan 2. Do not add `/auth/register`, `/auth/refresh`, `/auth/logout`, or rework `users.py` beyond what's listed in a task below.
- Every task must leave the repo in a state where `pip install -r src/requirements.txt` succeeds and `python -c "import app.main"` (run from `src/`) succeeds — no task may end with a broken import chain.
- Tests run from the repo root as: `cd src && python -m pytest tests/<file>.py -v` (pytest config lives at `src/pytest.ini` after Task 1).
- Task 4 (Alembic migration) requires a running Postgres reachable via `docker-compose.yml`'s `db` service. If Docker is unavailable when that task is dispatched, stop and report BLOCKED rather than skipping live verification.

---

### Task 1: Remove garbage files, prune dead dependencies, clean config.yaml

**Files:**
- Delete: `server.pas`
- Delete: `.coverage`
- Delete: `src/used.txt`
- Delete: `src/tests/LottyABPlatform.postman_collection.json`
- Delete: `src/tests/TESTING_REPORT.md`
- Delete: `src/tests/conftest.py`
- Delete: `src/tests/test_auth_and_users.py`
- Delete: `src/tests/requirements-test.txt`
- Delete: `src/tests/pytest.ini`
- Create: `src/pytest.ini`
- Modify: `src/requirements.txt` (full rewrite, UTF-8)
- Modify: `configs/config.yaml` (full rewrite)
- Test: `src/tests/test_repo_hygiene.py`

**Interfaces:**
- Produces: `src/pytest.ini` (pytest config location all later tasks' tests rely on), pruned `src/requirements.txt`, cleaned `configs/config.yaml` (sections: `app`, `run`, `logging`, `token`, `db` only).

- [ ] **Step 1: Delete the garbage/dead files**

Run from repo root:

```bash
rm -f server.pas .coverage src/used.txt
rm -f src/tests/LottyABPlatform.postman_collection.json
rm -f src/tests/TESTING_REPORT.md
rm -f src/tests/conftest.py
rm -f src/tests/test_auth_and_users.py
rm -f src/tests/requirements-test.txt
rm -f src/tests/pytest.ini
```

- [ ] **Step 2: Create `src/pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
pythonpath = .
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = -v --tb=short --strict-markers
markers =
    integration: integration tests touching multiple modules
    negative: negative / error path tests
    slow: slow tests
```

- [ ] **Step 3: Rewrite `src/requirements.txt` as UTF-8, pruning unused packages**

Remove `aioredis`, `redis`, `hiredis`, `fastapi-cache2`, `fastar`, `fastapi-swagger-dark`, `pendulum`, `sentry-sdk`, `dnspython` (all remnants of the config.yaml cache/exp_index block being deleted in Step 5, or unexplained/unused packages — grep confirms zero references to any of them under `src/app`). Keep everything else, including `sqlmodel` (still used until Task 5 of this plan removes it). Write the file with a plain UTF-8 encoder (the original was UTF-16LE, which is why it's being fully rewritten rather than edited):

```python
packages = """aiosqlite==0.22.1
alembic==1.18.1
annotated-doc==0.0.4
annotated-types==0.7.0
anyio==4.12.1
argon2-cffi==25.1.0
argon2-cffi-bindings==25.1.0
async-timeout==5.0.1
asyncpg==0.31.0
certifi==2026.1.4
cffi==2.0.0
click==8.3.1
colorama==0.4.6
dynaconf==3.2.12
email-validator==2.3.0
fastapi==0.128.0
fastapi-cli==0.0.20
fastapi-cloud-cli==0.11.0
greenlet==3.3.0
h11==0.16.0
httpcore==1.0.9
httptools==0.7.1
httpx==0.28.1
idna==3.11
iniconfig==2.3.0
Jinja2==3.1.6
lark==1.3.1
loguru==0.7.3
Mako==1.3.10
markdown-it-py==4.0.0
MarkupSafe==3.0.3
mdurl==0.1.2
packaging==26.0
passlib==1.7.4
pluggy==1.6.0
pycparser==2.23
pydantic==2.12.5
pydantic-extra-types==2.11.0
pydantic-settings==2.12.0
pydantic_core==2.41.5
Pygments==2.19.2
PyJWT==2.10.1
pytest==9.0.2
pytest-asyncio==1.3.0
python-dateutil==2.9.0.post0
python-dotenv==1.2.1
python-multipart==0.0.21
pytz==2025.2
PyYAML==6.0.3
rich==14.2.0
rich-toolkit==0.17.1
rignore==0.7.6
ruff==0.14.13
shellingham==1.5.4
six==1.17.0
SQLAlchemy==2.0.45
sqlmodel==0.0.31
starlette==0.50.0
typer==0.21.1
typing-inspection==0.4.2
typing_extensions==4.15.0
tzdata==2025.3
urllib3==2.6.3
uvicorn==0.40.0
watchfiles==1.1.1
websockets==16.0
win32_setctime==1.2.0
"""
with open("src/requirements.txt", "w", encoding="utf-8", newline="\n") as f:
    f.write(packages)
```

Run this as a one-off Python snippet (or write the file directly with a text editor set to UTF-8 — just do not reuse the old UTF-16LE file).

- [ ] **Step 4: Rewrite `configs/config.yaml`**

Remove the `cache`, `restrictions`, and `exp_index` blocks (unused remnants of an unrelated project — grepping `src/app` confirms no code reads `settings.cache`, `settings.restrictions`, or `settings.exp_index`), and fix `app.name`:

```yaml
app:
  name: FastAPI-Fish

run:
  host: 0.0.0.0
  port: 8080

logging:
  console:
    level: INFO
    enqueue: true
    backtrace: true
    diagnose: true
    format: "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>"
  file:
    path: logs/app.log
    rotation: 10 MB
    retention: 10 days
    compression: zip
    level: INFO
    enqueue: true
    backtrace: true
    diagnose: false

token:
  default_type: bearer
  schema: argon2
  access_token:
    lifetime_seconds: 3600
    algorithm: HS256
    expire_minutes: 120
  refresh_token:
    expire_days: 15

db:
  driver: postgresql+asyncpg
  echo: false
  echo_pool: false
  pool_size: 50
  max_overflow: 10
```

- [ ] **Step 5: Write the hygiene test**

```python
# src/tests/test_repo_hygiene.py
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_garbage_files_are_gone():
    assert not (REPO_ROOT / "server.pas").exists()
    assert not (REPO_ROOT / "src" / "tests" / "LottyABPlatform.postman_collection.json").exists()
    assert not (REPO_ROOT / "src" / "tests" / "conftest.py").exists()
    assert not (REPO_ROOT / "src" / "tests" / "test_auth_and_users.py").exists()


def test_requirements_txt_is_utf8_and_pruned():
    text = (REPO_ROOT / "src" / "requirements.txt").read_text(encoding="utf-8")
    for banned in ("aioredis", "fastapi-cache2", "hiredis", "sentry-sdk", "pendulum", "dnspython", "fastar", "fastapi-swagger-dark"):
        assert banned not in text, f"{banned} should have been pruned"
    assert "SQLAlchemy" in text


def test_config_yaml_has_no_unrelated_project_cruft():
    text = (REPO_ROOT / "configs" / "config.yaml").read_text(encoding="utf-8")
    assert "NoteManager" not in text
    assert "exp_index" not in text
    assert "restrictions" not in text
    assert "cache" not in text.split("token:")[0]  # crude but sufficient: no top-level cache: block
```

- [ ] **Step 4: Run the test**

```bash
cd src && python -m pytest tests/test_repo_hygiene.py -v
```

Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: remove dead-project artifacts and prune unused dependencies"
```

---

### Task 2: Fix dead imports and the `ADMN`→`ADMIN` typo so the app boots

**Files:**
- Modify: `src/app/infrastructure/repositories/__init__.py`
- Modify: `src/app/infrastructure/unit_of_work/uow_sqlmodel.py`
- Modify: `src/app/services/__init__.py`
- Modify: `src/app/api/v1/endpoints/__init__.py`
- Modify: `src/app/core/schemas/user.py:13-15`
- Modify: `src/app/services/user_service.py:27`
- Modify: `src/app/api/v1/dependencies/current_user.py:30,36`
- Test: `src/tests/test_app_boot.py`

**Interfaces:**
- Consumes: nothing new (fixes existing modules in place).
- Produces: `UserRole.ADMIN` (renamed from `ADMN`) — every later task and Plan 2/3 use `UserRole.ADMIN`. A working `app.main:app` import chain.

- [ ] **Step 1: Trim `app/infrastructure/repositories/__init__.py` to only what exists**

```python
from app.infrastructure.repositories.base_repo import BaseRepository
from app.infrastructure.repositories.user_repository import UserRepository

__all__ = ["BaseRepository", "UserRepository"]
```

- [ ] **Step 2: Trim `app/infrastructure/unit_of_work/uow_sqlmodel.py` to only `user_repo`**

```python
from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.repositories import UserRepository
from app.infrastructure.unit_of_work.abstract_uow import AbstractUnitOfWork


class UnitOfWork(AbstractUnitOfWork):
    user_repo: UserRepository

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __aenter__(self) -> Self:
        self.user_repo = UserRepository(self.session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc:
            await self.rollback()
        else:
            await self.commit()
        await self.session.close()

    async def commit(self) -> None:
        if self.session:
            await self.session.commit()

    async def rollback(self) -> None:
        if self.session:
            await self.session.rollback()
```

- [ ] **Step 3: Trim `app/services/__init__.py` to only what exists**

```python
from .auth_service import AuthService
from .jwt_service import JWTService
from .user_service import UserService

__all__ = ["AuthService", "JWTService", "UserService"]
```

- [ ] **Step 4: Trim `app/api/v1/endpoints/__init__.py` to only what exists**

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

- [ ] **Step 5: Fix the `ADMN` → `ADMIN` typo everywhere it appears**

`src/app/core/schemas/user.py` lines 13-15, change:
```python
class UserRole(str, Enum):
    ADMN = "ADMN"
    USER = "USER"
```
to:
```python
class UserRole(str, Enum):
    ADMIN = "ADMIN"
    USER = "USER"
```

`src/app/services/user_service.py` line 27, change:
```python
        return role == UserRole.ADMN
```
to:
```python
        return role == UserRole.ADMIN
```

`src/app/api/v1/dependencies/current_user.py` lines 30 and 36, change both:
```python
    if not _user_has_role(current_user, UserRole.ADMN):
```
and
```python
    if not any([_user_has_role(current_user, r) for r in [UserRole.ADMN]]):
```
to use `UserRole.ADMIN`.

- [ ] **Step 6: Write the boot smoke test**

```python
# src/tests/test_app_boot.py
from fastapi.testclient import TestClient

from app.main import app


def test_app_imports_and_ping_responds():
    client = TestClient(app)
    response = client.get("/api/v1/ping")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_user_role_has_no_typo():
    from app.core.schemas.user import UserRole

    assert UserRole.ADMIN.value == "ADMIN"
    assert not hasattr(UserRole, "ADMN")
```

- [ ] **Step 7: Run the test**

```bash
cd src && python -m pytest tests/test_app_boot.py -v
```

Expected: 2 passed. (This is the first point in the plan where `app.main` actually imports successfully.)

- [ ] **Step 8: Commit**

```bash
git add -A
git commit -m "fix: remove dead cross-domain imports and ADMN typo so the app boots"
```

---

### Task 3: SQLAlchemy 2.0 declarative models — `User`, `RefreshToken`

**Files:**
- Create: `src/app/core/enums.py`
- Create: `src/app/infrastructure/models/base.py`
- Modify: `src/app/infrastructure/models/user.py` (full rewrite)
- Create: `src/app/infrastructure/models/refresh_token.py`
- Modify: `src/app/infrastructure/models/__init__.py`
- Modify: `src/app/core/schemas/user.py` (replace local `UserRole` definition with an import from `app.core.enums`)
- Test: `src/tests/test_models.py`

**Interfaces:**
- Consumes: `UserRole.ADMIN`/`UserRole.USER` fixed in Task 2.
- Produces: `app.core.enums.UserRole` (the **single** canonical role enum from this task onward — `app/core/schemas/user.py` no longer defines its own), `app.infrastructure.models.Base` (declarative base, `Base.metadata` used by Alembic in Task 4), `app.infrastructure.models.User` and `app.infrastructure.models.RefreshToken` with snake_case columns (`full_name`, `is_active`, `created_by`, `created_at`, `updated_at`, `user_id`, `hashed_token`, `expires_at`) — Task 5's repositories and Plan 2's services consume these exact column/attribute names.

- [ ] **Step 1: Create `app/core/enums.py`**

```python
from enum import Enum


class UserRole(str, Enum):
    USER = "USER"
    ADMIN = "ADMIN"
```

- [ ] **Step 2: Point `app/core/schemas/user.py`'s `UserRole` at the new canonical enum**

Replace lines 1-15 (the `Enum` import and the local `class UserRole(str, Enum): ...` block) so the file starts:

```python
from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import AfterValidator, EmailStr, Field

from app.core.enums import UserRole
from app.core.schemas.base import DatetimeResponse, PyModel
from app.core.schemas.token import Token
from app.core.utils import check_len_password

__all__ = ["UserRole"]
```

Leave the rest of the file (`UserUpdateBody`, `UserCreateBody`, `UserLoginBody`, `UserData`, `UserReadResponse`, `UserWithTokenResponse`, `TokenData`) unchanged — they still reference `UserRole`, which now resolves to the imported enum with the same two members (`USER`, `ADMIN`), so no other line in this file changes.

- [ ] **Step 3: Create `app/infrastructure/models/base.py`**

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

- [ ] **Step 4: Rewrite `app/infrastructure/models/user.py`**

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Enum as SAEnum, ForeignKey, String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import UserRole
from app.infrastructure.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(
            UserRole,
            name="user_role",
            native_enum=False,
            length=20,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True, precision=6),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True, precision=6),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    creator: Mapped["User | None"] = relationship(remote_side=[id])
```

- [ ] **Step 5: Create `app/infrastructure/models/refresh_token.py`**

```python
import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.models.base import Base


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    __table_args__ = (
        Index("idx_refresh_tokens_user_id", "user_id"),
        Index("idx_refresh_tokens_hashed_token", "hashed_token"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    hashed_token: Mapped[str] = mapped_column(String(255), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True, precision=6), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True, precision=6),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
```

- [ ] **Step 6: Rewrite `app/infrastructure/models/__init__.py`**

```python
from app.infrastructure.models.base import Base
from app.infrastructure.models.refresh_token import RefreshToken
from app.infrastructure.models.user import User

__all__ = ["Base", "RefreshToken", "User"]
```

- [ ] **Step 7: Write the model test (uses an in-memory SQLite engine — no Postgres needed for this task)**

```python
# src/tests/test_models.py
from sqlalchemy import create_engine, inspect

from app.core.enums import UserRole
from app.infrastructure.models import Base, RefreshToken, User


def test_tables_have_expected_columns():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)

    assert set(inspector.get_table_names()) == {"users", "refresh_tokens"}

    user_columns = {c["name"] for c in inspector.get_columns("users")}
    assert user_columns == {
        "id", "email", "password", "full_name", "role",
        "is_active", "created_by", "created_at", "updated_at",
    }

    token_columns = {c["name"] for c in inspector.get_columns("refresh_tokens")}
    assert token_columns == {"id", "user_id", "hashed_token", "expires_at", "created_at"}


def test_user_role_enum_values():
    assert {member.value for member in UserRole} == {"USER", "ADMIN"}


def test_schemas_user_role_is_the_canonical_enum():
    from app.core.schemas.user import UserRole as SchemaUserRole

    assert SchemaUserRole is UserRole
```

- [ ] **Step 8: Run the test**

```bash
cd src && python -m pytest tests/test_models.py -v
```

Expected: 3 passed.

- [ ] **Step 9: Commit**

```bash
git add -A
git commit -m "feat: add SQLAlchemy 2.0 declarative User and RefreshToken models"
```

---

### Task 4: Alembic migration 1:1 with KotlinFish's `V1__init.sql`

**Files:**
- Modify: `src/alembic/env.py`
- Create: `src/alembic/versions/0001_initial_schema.py`
- Test: manual `alembic upgrade head` / `alembic downgrade base` against the `db` service from `docker-compose.yml`

**Interfaces:**
- Consumes: `app.infrastructure.models.Base` from Task 3.
- Produces: live `users` and `refresh_tokens` tables in Postgres matching the DDL below exactly — Task 5's repositories and every later plan assume these tables exist.

- [ ] **Step 1: Point `alembic/env.py` at the new `Base.metadata`**

Replace:
```python
import app.infrastructure.models
from app.core.config import settings

...

from sqlmodel import SQLModel
...
target_metadata = SQLModel.metadata
```
with:
```python
from app.core.config import settings
from app.infrastructure.models import Base

...

target_metadata = Base.metadata
```
(Remove the `import app.infrastructure.models` side-effect-only import and the `from sqlmodel import SQLModel` import; keep every other line of `env.py` — `run_migrations_offline`, `do_run_migrations`, `run_async_migrations`, `run_migrations_online` — unchanged.)

- [ ] **Step 2: Write the migration by hand** (exact DDL match, not autogenerate, so precision/constraints match the spec exactly)

```python
# src/alembic/versions/0001_initial_schema.py
"""initial schema: users, refresh_tokens

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-10
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True, precision=6), nullable=False),
        sa.Column("updated_at", postgresql.TIMESTAMP(timezone=True, precision=6), nullable=False),
        sa.CheckConstraint("role IN ('USER', 'ADMIN')", name="ck_users_role"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_users_created_by_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("hashed_token", sa.String(length=255), nullable=False),
        sa.Column("expires_at", postgresql.TIMESTAMP(timezone=True, precision=6), nullable=False),
        sa.Column("created_at", postgresql.TIMESTAMP(timezone=True, precision=6), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_refresh_tokens_user_id_users"),
    )
    op.create_index("idx_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("idx_refresh_tokens_hashed_token", "refresh_tokens", ["hashed_token"])


def downgrade() -> None:
    op.drop_index("idx_refresh_tokens_hashed_token", table_name="refresh_tokens")
    op.drop_index("idx_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
```

- [ ] **Step 3: Verify against a live Postgres**

```bash
docker compose up -d db
# wait for healthy, then from src/:
cd src
alembic upgrade head
```

Expected: no errors; `alembic current` shows `0001_initial_schema (head)`.

Then verify the schema matches:

```bash
docker compose exec db psql -U postgres -d prodindivid -c "\d users"
docker compose exec db psql -U postgres -d prodindivid -c "\d refresh_tokens"
```

Expected: columns/types/constraints match the DDL in this task exactly (including the `ck_users_role` check constraint and both indexes on `refresh_tokens`).

Then verify reversibility:

```bash
alembic downgrade base
alembic upgrade head
```

Expected: both succeed with no errors.

If Docker is not available in the execution environment, stop and report BLOCKED — do not mark this task complete without a live-Postgres verification, since the DDL fidelity (exact column types, `TIMESTAMP(6)`, the check constraint) is the entire point of this task and cannot be confirmed by SQLite or offline SQL rendering alone.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: add Alembic migration 0001 for users and refresh_tokens tables"
```

---

### Task 5: Rewire repositories and UnitOfWork onto the new models; remove SQLModel entirely

**Files:**
- Modify: `src/app/infrastructure/repositories/base_repo.py`
- Modify: `src/app/infrastructure/repositories/user_repository.py` (full rewrite)
- Create: `src/app/infrastructure/repositories/refresh_token_repository.py`
- Modify: `src/app/infrastructure/repositories/__init__.py`
- Delete: `src/app/infrastructure/unit_of_work/uow_sqlmodel.py`
- Create: `src/app/infrastructure/unit_of_work/uow.py`
- Modify: `src/app/infrastructure/unit_of_work/__init__.py`
- Modify: `src/app/api/v1/dependencies/session.py`
- Modify: `src/app/core/schemas/base.py`
- Modify: `src/app/actions/first_admin.py`
- Modify: `src/requirements.txt` (remove `sqlmodel`)
- Test: `src/tests/test_unit_of_work.py`

**Interfaces:**
- Consumes: `app.infrastructure.models.{User,RefreshToken}` from Task 3, the live schema from Task 4.
- Produces: `UnitOfWork.user_repo` (`UserRepository`) and `UnitOfWork.refresh_token_repo` (`RefreshTokenRepository`) — Plan 2's `AuthService`/`UserService` consume both. `BaseRepository.update(id_, dict)` now takes a plain `dict[str, Any]` instead of a `PyModel` — any future repository subclass follows this signature.

- [ ] **Step 1: Rewrite `base_repo.py` to drop the `PyModel`/SQLModel dependency**

```python
# src/app/infrastructure/repositories/base_repo.py
from typing import Any, Generic
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.custom_types import T
from app.core.exceptions.base import DuplicateError, RepositoryError


class BaseRepository(Generic[T]):
    def __init__(self, session: AsyncSession, model: type[T]) -> None:
        self.session = session
        self.model = model

    async def add(self, obj: T) -> T:
        try:
            self.session.add(obj)
            await self.session.flush()
            await self.session.refresh(obj)
            return obj
        except IntegrityError as e:
            raise DuplicateError("Unique field already exists") from e
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def deactivate(self, id_: UUID, **values: Any) -> None:
        stmt = update(self.model).where(self.model.id == id_).values(**values)
        try:
            await self.session.execute(stmt)
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def update(self, id_: UUID, new_data: dict[str, Any]) -> T | None:
        stmt = (
            update(self.model)
            .where(self.model.id == id_)
            .values(**new_data)
            .returning(self.model)
        )
        try:
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def get_by_id(self, id_: UUID) -> T | None:
        try:
            stmt = select(self.model).where(self.model.id == id_)
            res = await self.session.execute(stmt)
            return res.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def get_all(self) -> list[T]:
        try:
            res = await self.session.execute(select(self.model))
            return list(res.scalars().all())
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def get_paginated(self, offset: int, limit: int) -> list[T]:
        try:
            q = select(self.model).offset(offset).limit(limit)
            result = await self.session.execute(q)
            return list(result.scalars().all())
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def count(self) -> int:
        q = select(func.count()).select_from(self.model)
        result = await self.session.execute(q)
        return result.scalar_one()
```

- [ ] **Step 2: Rewrite `user_repository.py`** (drops the `User.roles` bug — `User.role` is a scalar column now, and `get_by_id` no longer needs a buggy override since the base class already does the right thing)

```python
# src/app/infrastructure/repositories/user_repository.py
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.base import RepositoryError
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
```

- [ ] **Step 3: Create `refresh_token_repository.py`**

```python
# src/app/infrastructure/repositories/refresh_token_repository.py
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions.base import RepositoryError
from app.infrastructure.models import RefreshToken
from app.infrastructure.repositories.base_repo import BaseRepository


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, model=RefreshToken)

    async def get_by_user_and_hash(self, user_id: UUID, hashed_token: str) -> RefreshToken | None:
        stmt = select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.hashed_token == hashed_token,
        )
        try:
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def delete_by_hash(self, hashed_token: str) -> None:
        stmt = delete(RefreshToken).where(RefreshToken.hashed_token == hashed_token)
        try:
            await self.session.execute(stmt)
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e

    async def delete_all_for_user(self, user_id: UUID) -> None:
        stmt = delete(RefreshToken).where(RefreshToken.user_id == user_id)
        try:
            await self.session.execute(stmt)
        except SQLAlchemyError as e:
            raise RepositoryError("Database error") from e
```

- [ ] **Step 4: Update `repositories/__init__.py`**

```python
from app.infrastructure.repositories.base_repo import BaseRepository
from app.infrastructure.repositories.refresh_token_repository import RefreshTokenRepository
from app.infrastructure.repositories.user_repository import UserRepository

__all__ = ["BaseRepository", "RefreshTokenRepository", "UserRepository"]
```

- [ ] **Step 5: Delete `uow_sqlmodel.py`, create `uow.py`**

```bash
rm src/app/infrastructure/unit_of_work/uow_sqlmodel.py
```

```python
# src/app/infrastructure/unit_of_work/uow.py
from types import TracebackType
from typing import Self

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.repositories import RefreshTokenRepository, UserRepository
from app.infrastructure.unit_of_work.abstract_uow import AbstractUnitOfWork


class UnitOfWork(AbstractUnitOfWork):
    user_repo: UserRepository
    refresh_token_repo: RefreshTokenRepository

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def __aenter__(self) -> Self:
        self.user_repo = UserRepository(self.session)
        self.refresh_token_repo = RefreshTokenRepository(self.session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc:
            await self.rollback()
        else:
            await self.commit()
        await self.session.close()

    async def commit(self) -> None:
        if self.session:
            await self.session.commit()

    async def rollback(self) -> None:
        if self.session:
            await self.session.rollback()
```

- [ ] **Step 6: Update `unit_of_work/__init__.py`**

```python
# src/app/infrastructure/unit_of_work/__init__.py
from app.infrastructure.unit_of_work.abstract_uow import AbstractUnitOfWork
from app.infrastructure.unit_of_work.uow import UnitOfWork

__all__ = ["AbstractUnitOfWork", "UnitOfWork"]
```

- [ ] **Step 7: Fix `session.py` to import `AsyncSession` from SQLAlchemy, not SQLModel**

```python
# src/app/api/v1/dependencies/session.py
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.db_helper import db_helper

SessionDep = Annotated[AsyncSession, Depends(db_helper.session_getter)]
```

- [ ] **Step 8: Rewrite `schemas/base.py`'s `PyModel` to subclass plain Pydantic, not SQLModel**

```python
# src/app/core/schemas/base.py
from datetime import datetime, timezone

from pydantic import BaseModel, field_serializer


class PyModel(BaseModel):
    pass


class DatetimeResponse(PyModel):
    @field_serializer("createdAt", "updatedAt", check_fields=False)
    def serialize_dt(self, dt: datetime, _info) -> str:
        utc_dt = dt.astimezone(timezone.utc)
        iso_str = utc_dt.isoformat()
        if iso_str.endswith("+00:00"):
            return iso_str[:-9] + "Z"
        return iso_str[:-3] + "Z"
```

- [ ] **Step 9: Fix `first_admin.py` to use the new SQLAlchemy model and snake_case fields**

```python
# src/app/actions/first_admin.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.hash import argon2

from app.core.config import settings
from app.core.enums import UserRole
from app.core.logger import Logger
from app.infrastructure.models.user import User


async def create_admin(session: AsyncSession):
    email = settings.ADMIN_EMAIL
    logger = Logger().get_logger()

    stmt = select(User).where(User.email == email)
    result = await session.execute(stmt)
    admin = result.scalar_one_or_none()

    if admin:
        logger.warning(f"User {email} already exists!")
        return

    new_admin = User(
        email=email,
        password=argon2.hash(settings.ADMIN_PASSWORD),
        full_name=settings.ADMIN_FULLNAME,
        role=UserRole.ADMIN,
        is_active=True,
    )
    session.add(new_admin)

    await session.flush()
    await session.commit()
    await session.refresh(new_admin)

    logger.info(f"Admin {email} successfully created!")
```

- [ ] **Step 10: Remove `sqlmodel` from `src/requirements.txt`**

Delete the `sqlmodel==0.0.31` line. Nothing else in the file changes.

- [ ] **Step 11: Grep to confirm no SQLModel references remain**

```bash
grep -ril sqlmodel src/app || echo "clean"
```

Expected: `clean` (no output from grep, since it's piped through `||`).

- [ ] **Step 12: Write the UnitOfWork/repository integration test** (uses SQLite via aiosqlite so it runs without Docker; Task 4 already proved the same models work against real Postgres)

```python
# src/tests/test_unit_of_work.py
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.enums import UserRole
from app.infrastructure.models import Base, User
from app.infrastructure.unit_of_work import UnitOfWork


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


async def test_user_repo_add_and_get_by_email(session_factory):
    async with session_factory() as session:
        uow = UnitOfWork(session)
        async with uow:
            user = User(
                id=uuid.uuid4(),
                email="fish@example.com",
                password="hashed",
                full_name="Fish Admin",
                role=UserRole.ADMIN,
                is_active=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.user_repo.add(user)

    async with session_factory() as session:
        uow = UnitOfWork(session)
        async with uow:
            found = await uow.user_repo.get_by_email("fish@example.com")
            assert found is not None
            assert found.role == UserRole.ADMIN
            assert found.full_name == "Fish Admin"


async def test_refresh_token_repo_roundtrip(session_factory):
    from app.infrastructure.models import RefreshToken
    from datetime import timedelta

    user_id = uuid.uuid4()
    async with session_factory() as session:
        uow = UnitOfWork(session)
        async with uow:
            user = User(
                id=user_id,
                email="rt@example.com",
                password="hashed",
                full_name="RT User",
                role=UserRole.USER,
                is_active=True,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            await uow.user_repo.add(user)
            token = RefreshToken(
                id=uuid.uuid4(),
                user_id=user_id,
                hashed_token="abc123",
                expires_at=datetime.now(UTC) + timedelta(days=30),
                created_at=datetime.now(UTC),
            )
            await uow.refresh_token_repo.add(token)

    async with session_factory() as session:
        uow = UnitOfWork(session)
        async with uow:
            found = await uow.refresh_token_repo.get_by_user_and_hash(user_id, "abc123")
            assert found is not None
            await uow.refresh_token_repo.delete_by_hash("abc123")

    async with session_factory() as session:
        uow = UnitOfWork(session)
        async with uow:
            gone = await uow.refresh_token_repo.get_by_user_and_hash(user_id, "abc123")
            assert gone is None
```

- [ ] **Step 13: Run all Plan 1 tests together**

```bash
cd src && python -m pytest tests/ -v
```

Expected: all tests from Tasks 1, 2, 3, and 5 pass (`test_repo_hygiene.py`, `test_app_boot.py`, `test_models.py`, `test_unit_of_work.py`).

- [ ] **Step 14: Commit**

```bash
git add -A
git commit -m "refactor: rewire repositories and UnitOfWork onto SQLAlchemy models, drop SQLModel"
```

---

## Self-Review Notes

- **Spec coverage:** This plan covers spec stage 1 ("Чистка мусора и починка UnitOfWork/сервисов") and stage 2 ("Модель БД + Alembic-миграция 1:1 с DDL") in full. Auth flow, users CRUD contract, error/validation format, observability, templating, and tests/CI are explicitly deferred to Plans 2-4, per the spec's own staging.
- **Known follow-ups for Plan 2:** `users.py` still calls `user_service.get_current_by_id` (doesn't exist) and `user_service.register` (doesn't exist) inside endpoint bodies — these don't block import/boot (Task 2's smoke test proves this) but do mean `GET/PUT /users/me` and `POST /users` will 500 at runtime until Plan 2 rewrites `users.py` and `UserService`. `AuthService.login_user` still only issues an access token (no refresh token/cookie rotation) until Plan 2. This is intentional — flagging here so the final Plan 1 review doesn't treat it as a regression.
- **Type consistency check:** `UserRole` is defined once (`app.core.enums.UserRole`) and imported everywhere (`app/infrastructure/models/user.py`, `app/core/schemas/user.py`, `app/actions/first_admin.py`) — no duplicate enum. `BaseRepository.update` signature (`dict[str, Any]`) is consistent between `base_repo.py` and its only override in `user_repository.py`. `UnitOfWork.user_repo`/`refresh_token_repo` names are consistent across `uow.py`, the test file, and this plan's Interfaces blocks.
