# FastAPI-Fish Stage 5: Postgres Integration Tests & CI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the last two parity gaps with `KotlinFish`: today's test suite only runs against
in-memory SQLite (Kotlin's `*IT.kt` suite runs against real Postgres via Testcontainers), and
there's no CI at all (Kotlin has `ktlintCheck` + tests on every push/PR). This plan adds a
Postgres-backed integration test suite via `testcontainers-python` and a
`.github/workflows/ci.yml` that runs `ruff check` + the full pytest suite (unit + integration).

**Architecture:** New `src/tests/integration/` package with its own `conftest.py`, reusing the
existing unit-test fixture pattern from `src/tests/conftest.py` (extracted into a small shared
helper so both suites stay in sync). Unit tests keep running on in-memory SQLite unchanged — this
plan is additive, not a replacement.

**Tech Stack:** `testcontainers` (Python, `testcontainers.postgres.PostgresContainer`) spins up a
real `postgres:15-alpine` container per test session, same async SQLAlchemy/asyncpg stack the app
already uses. GitHub Actions `ubuntu-latest` (Docker preinstalled, same as Kotlin's Testcontainers
CI setup — no explicit Postgres service container needed in the workflow).

## Global Constraints

- **Prerequisite:** run this plan on top of `docs/superpowers/plans/2026-08-12-fastapi-fish-stage3-contract-observability.md` — Task 1 below refactors the exact `client` fixture shape that Stage 3's Task 7 produces in `src/tests/conftest.py`. If Stage 3 hasn't landed, `src/tests/conftest.py` won't match what Step 2 below expects to find — do Stage 3 first.
- Integration tests must be skip-safe when Docker isn't available locally (not everyone running `pytest` has Docker running) — they should skip, not error.
- Don't change unit-test behavior or fixtures' external names (`client`, `db_session_factory`, `admin_headers` in `src/tests/conftest.py` keep their signatures) — only extract shared internals.
- Run the unit suite with: `cd src && python -m pytest -m "not integration"` (no Docker needed).
- Run the integration suite with: `cd src && python -m pytest -m integration` (needs Docker running locally).

---

### Task 1: Postgres-backed integration test suite

**Files:**
- Modify: `src/requirements.txt`
- Modify: `src/tests/conftest.py`
- Create: `src/tests/integration/conftest.py`
- Create: `src/tests/integration/test_auth_flow_it.py`
- Create: `src/tests/integration/test_users_crud_it.py`

**Interfaces:**
- Produces: `_client_bound_to(session_factory)` async context manager in `tests.conftest`, reused by `tests/integration/conftest.py`. `postgres_container` (session-scoped), `pg_session_factory`, `client`, `admin_headers` fixtures in `tests/integration/conftest.py` — same names/shapes as the unit suite's fixtures, but backed by a real Postgres container instead of in-memory SQLite.

- [ ] **Step 1: Add the `testcontainers` dependency**

Add to `src/requirements.txt` (alphabetically, near `starlette`/`typer`):

```
testcontainers==4.9.2
```

Install it: `cd src && pip install testcontainers==4.9.2`

(If that exact pin fails to resolve, install the latest available `testcontainers` release instead and update this line — the Postgres module's API used below, `PostgresContainer(image).username/.password/.dbname/.get_container_host_ip()/.get_exposed_port()`, has been stable across recent 4.x releases.)

- [ ] **Step 2: Extract the shared client-fixture helper**

In `src/tests/conftest.py`, this is the expected current state (post Stage-3 Task 7):

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

Replace it with:

```python
from contextlib import asynccontextmanager


@asynccontextmanager
async def _client_bound_to(session_factory):
    async def override_session_getter():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[db_helper.session_getter] = override_session_getter
    original_session_factory = db_helper.session_factory
    db_helper.session_factory = session_factory

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        db_helper.session_factory = original_session_factory
        app.dependency_overrides.clear()


@pytest.fixture
async def client(db_session_factory):
    async with _client_bound_to(db_session_factory) as test_client:
        yield test_client
```

(Add the `from contextlib import asynccontextmanager` import at the top of the file with the other imports.)

- [ ] **Step 3: Run the unit suite to confirm the refactor is behavior-preserving**

Run: `cd src && python -m pytest -m "not integration" -v`
Expected: all PASS, identical to before the refactor (this step has no new tests — it's the safety check for Step 2).

- [ ] **Step 4: Create the integration test package's `conftest.py`**

Create `src/tests/integration/conftest.py`:

```python
import shutil
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from testcontainers.postgres import PostgresContainer

from app.core.enums import UserRole
from app.infrastructure.models import Base, User
from app.services.jwt_service import JWTService
from tests.conftest import _client_bound_to


@pytest.fixture(scope="session")
def postgres_container():
    if shutil.which("docker") is None:
        pytest.skip("Docker is not available - skipping Postgres integration tests")

    with PostgresContainer("postgres:15-alpine") as container:
        yield container


@pytest.fixture
async def pg_session_factory(postgres_container):
    url = (
        f"postgresql+asyncpg://{postgres_container.username}:{postgres_container.password}"
        f"@{postgres_container.get_container_host_ip()}:{postgres_container.get_exposed_port(5432)}"
        f"/{postgres_container.dbname}"
    )
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(bind=engine, expire_on_commit=False)
    yield factory

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def client(pg_session_factory):
    async with _client_bound_to(pg_session_factory) as test_client:
        yield test_client


@pytest.fixture
async def admin_headers(pg_session_factory, client):
    admin_id = uuid.uuid4()
    now = datetime.now(UTC)
    async with pg_session_factory() as session:
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

This mirrors `src/tests/conftest.py`'s `db_session_factory`/`client`/`admin_headers` fixtures
exactly, swapping the in-memory SQLite engine for a real Postgres container. The
`postgres_container` fixture's `pytest.skip()` propagates to every test that depends on it
(directly or via `pg_session_factory`/`client`/`admin_headers`), so the whole integration suite
skips cleanly when Docker isn't available instead of erroring.

- [ ] **Step 5: Write the full auth-flow integration test**

Create `src/tests/integration/test_auth_flow_it.py`:

```python
import pytest

pytestmark = pytest.mark.integration


def test_full_auth_flow_against_real_postgres(client):
    register = client.post(
        "/api/v1/auth/register",
        json={"email": "flow@fish.io", "password": "password1", "fullName": "Flow Fish"},
    )
    assert register.status_code == 201
    old_refresh = register.cookies["refreshToken"]

    login = client.post("/api/v1/auth/login", json={"email": "flow@fish.io", "password": "password1"})
    assert login.status_code == 200

    refresh = client.post("/api/v1/auth/refresh")
    assert refresh.status_code == 200
    new_refresh = refresh.cookies["refreshToken"]
    assert new_refresh != old_refresh

    client.cookies.set("refreshToken", old_refresh)
    reuse_of_rotated_token = client.post("/api/v1/auth/refresh")
    assert reuse_of_rotated_token.status_code == 401

    client.cookies.set("refreshToken", new_refresh)
    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 204

    reuse_after_logout = client.post("/api/v1/auth/refresh")
    assert reuse_after_logout.status_code == 401
```

- [ ] **Step 6: Write the users CRUD / RBAC / pagination integration test**

Create `src/tests/integration/test_users_crud_it.py`:

```python
import pytest

pytestmark = pytest.mark.integration


def test_admin_can_list_paginate_and_filter_users(client, admin_headers):
    for i in range(3):
        client.post(
            "/api/v1/users",
            json={"email": f"user{i}@fish.io", "password": "password1", "fullName": f"User {i}"},
            headers=admin_headers,
        )

    page = client.get("/api/v1/users?page=0&size=2", headers=admin_headers)
    assert page.status_code == 200
    page_body = page.json()
    assert page_body["total"] >= 4  # 3 created here + the admin itself
    assert len(page_body["items"]) == 2

    filtered = client.get("/api/v1/users?email=user1", headers=admin_headers)
    assert filtered.status_code == 200
    filtered_body = filtered.json()
    assert filtered_body["total"] == 1
    assert filtered_body["items"][0]["email"] == "user1@fish.io"


def test_non_admin_cannot_change_own_role(client):
    register = client.post(
        "/api/v1/auth/register",
        json={"email": "self@fish.io", "password": "password1", "fullName": "Self Fish"},
    )
    access_token = register.json()["accessToken"]
    headers = {"Authorization": f"Bearer {access_token}"}

    response = client.put(
        "/api/v1/users/me",
        json={"fullName": "Self Fish", "role": "ADMIN", "isActive": True},
        headers=headers,
    )
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_admin_deactivating_user_revokes_their_refresh_token(client, admin_headers):
    register = client.post(
        "/api/v1/auth/register",
        json={"email": "revoke@fish.io", "password": "password1", "fullName": "Revoke Fish"},
    )
    user_id = register.json()["user"]["id"]
    refresh_cookie = register.cookies["refreshToken"]

    deactivate = client.delete(f"/api/v1/users/{user_id}", headers=admin_headers)
    assert deactivate.status_code == 204

    client.cookies.set("refreshToken", refresh_cookie)
    refresh_attempt = client.post("/api/v1/auth/refresh")
    assert refresh_attempt.status_code == 401
```

- [ ] **Step 7: Run the integration suite (requires Docker running locally)**

Run: `cd src && python -m pytest -m integration -v`
Expected: PASS (first run pulls `postgres:15-alpine`, which takes a bit longer). If Docker isn't
running, expected instead: tests reported as `SKIPPED` with reason "Docker is not available", not
`ERROR`.

- [ ] **Step 8: Run the full suite (unit + integration)**

Run: `cd src && python -m pytest -v`
Expected: all PASS.

- [ ] **Step 9: Commit**

```bash
git add src/requirements.txt src/tests/conftest.py src/tests/integration
git commit -m "test: add Postgres-backed integration suite via testcontainers"
```

---

### Task 2: `.github/workflows/ci.yml`

**Files:**
- Create: `.github/workflows/ci.yml`

**Interfaces:** None.

- [ ] **Step 1: Write the workflow**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: src
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: pip install -r requirements.txt
      - run: ruff check .

  test:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: src
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.13"
      - run: pip install -r requirements.txt
      - run: cp .env.example .env
      - name: Unit tests (in-memory SQLite)
        run: python -m pytest -m "not integration" -v
      - name: Integration tests (Testcontainers Postgres)
        run: python -m pytest -m integration -v
```

(No explicit Postgres service container is needed — `ubuntu-latest` ships Docker preinstalled,
and `testcontainers` uses it directly, the same way Kotlin's Testcontainers-based CI works.
Copying `.env.example` to `.env` gives `app.core.config`'s Dynaconf loader something to read;
none of its placeholder values need to be real for the test suite to run, since the unit suite
never touches Postgres and the integration suite gets its connection details from the
`testcontainers`-provisioned container, not from `.env`.)

- [ ] **Step 2: Verify the workflow is syntactically valid**

Run from the repo root (requires `actionlint`, or skip this step and rely on GitHub validating it
on the next push if `actionlint` isn't installed locally):

```bash
actionlint .github/workflows/ci.yml
```

If `actionlint` isn't available, at minimum confirm the YAML parses:

```bash
python -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
```

Expected: no errors.

- [ ] **Step 3: Push and confirm the workflow runs**

Push this branch (or open a PR) and check the Actions tab — both `lint` and `test` jobs should
run and pass. This is the real end-to-end verification; the local YAML check in Step 2 only
catches syntax errors, not runtime failures.

- [ ] **Step 4: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions workflow (ruff check + pytest)"
```

---

### Task 3: Verify `src/README.md`'s CI section still matches reality

Stage 4 wrote `src/README.md`'s CI section deliberately short — "runs `ruff check` and `pytest`;
see that workflow file for exactly what runs" — specifically so it wouldn't drift out of sync
with the real CI config. This task is a verification, not a code change.

**Files:**
- Read-only check against: `src/README.md`, `.github/workflows/ci.yml`

- [ ] **Step 1: Confirm the README's CI section is still accurate**

Read the "## CI" section of `src/README.md`. It should say the workflow runs `ruff check` and
`pytest` on every push/PR to `main`. Compare against the actual `.github/workflows/ci.yml` from
Task 2: two jobs, `lint` (`ruff check .`) and `test` (`pytest` twice — unit then integration).
The README's phrasing is intentionally general enough to already cover this — no edit needed.

- [ ] **Step 2: If it does need an edit**

Only if a future change to `ci.yml` adds something the README doesn't mention (e.g. a coverage
report, a matrix build) — update the "## CI" section in `src/README.md` to match, then:

```bash
git add src/README.md
git commit -m "docs: sync README CI section with actual workflow"
```

---

## After this plan

All three stages (3, 4, 5) together bring `FastAPI-Fish` to full parity with `KotlinFish`: same
API contract, same observability surface, same one-command fork workflow, same
Postgres-integration-tested CI safety net. At that point the two templates should be
interchangeable starting points for a new domain, differing only in language/framework.
