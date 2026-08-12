# FastAPI-Fish Stage 4: Templating & Forkability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `FastAPI-Fish` as easy to fork into a new domain as `KotlinFish` is today: a real `src/README.md` (currently empty), a one-command project-rename script (`actions/init-project.sh`/`.ps1`), and a script that exports the running app's OpenAPI schema to `docs/api-docs.json` — mirroring Kotlin's "Use this template" flow exactly.

**Architecture:** Purely additive/documentation work — no application code changes. New files live at the repo root under `actions/` (sibling to `src/`, matching where Kotlin's own `actions/init-project.sh` lives) and `docs/`.

**Tech Stack:** POSIX `sh` (via Git Bash, already used by `src/entrypoint.sh`) + PowerShell for the two rename-script variants, plain Python for the OpenAPI export (reuses the already-installed FastAPI app), pytest for testing the scripts via `subprocess`.

## Global Constraints

- **Prerequisite:** run this plan on top of `docs/superpowers/plans/2026-08-12-fastapi-fish-stage3-contract-observability.md` — the README documents the post-Stage-3 contract (health at `/health/liveness`/`/health/readiness`, `/metrics`, `APP_ADMIN_*`/`APP_CORS_ALLOWED_ORIGINS` env vars). If Stage 3 hasn't landed yet, stop and do that first.
- There are **two READMEs** in this repo — don't confuse them: the root `README.md` is the PROD-2026 olympiad's fixed contest instructions (not ours to touch). `src/README.md` is this project's real template documentation and is currently an **empty file** — that's what this plan fills in.
- Everything this plan adds must work from a fresh clone with nothing installed beyond what `src/requirements.txt` + Docker already provide.
- Run tests with: `cd src && python -m pytest` (needs `src/.env` populated from `src/.env.example`).

---

### Task 1: Write `src/README.md`

**Files:**
- Modify: `src/README.md` (currently empty)

**Interfaces:** None — pure documentation.

- [ ] **Step 1: Write the file**

Replace the full (empty) contents of `src/README.md` with:

````markdown
# Fish — FastAPI Backend Template

A production-ready starter template for a FastAPI REST API: JWT authentication with
refresh-token rotation, role-based authorization, PostgreSQL + Alembic migrations, request
validation, structured error handling, OpenAPI docs, and a pytest test suite wired into GitHub
Actions CI.

Use it as a `git init`-and-go base for a new service, or as a reference for how these pieces fit
together in a FastAPI project. It's the FastAPI counterpart to the
[`KotlinFish`](https://github.com/Wertiba/KotlinFish) Kotlin/Spring Boot template — same API
contract, same DB schema, same "fork and go" workflow.

## Features

- **Auth**: register/login/logout/refresh with access tokens (JWT) + rotating refresh tokens
  stored server-side, delivered via an `HttpOnly` cookie.
- **Authorization**: FastAPI dependencies enforcing role- and ownership-based access (e.g.
  "admin or self") on every protected route.
- **Users**: CRUD with pagination, filtering, and validation.
- **Database**: PostgreSQL via SQLAlchemy 2.0 (async), schema managed with Alembic migrations.
- **Errors**: centralized exception handling with a consistent `ErrorResponse` shape
  (`code`, `message`, `traceId`, `timestamp`, `path`, optional `details`/`fieldErrors`).
- **Docs**: OpenAPI/Swagger UI via FastAPI's built-in `/docs`.
- **Ops**: liveness/readiness probes (`/api/v1/health/liveness`, `/api/v1/health/readiness`)
  and a Prometheus metrics endpoint (`/api/v1/metrics`).
- **Logging**: a per-request trace ID (`X-Trace-Id` header), generated or echoed back on every
  response and embedded in `ErrorResponse.traceId`, so a client-visible error can be found
  verbatim in server logs. Colored, human-readable console output plus rotating file logs under
  `logs/` (loguru).
- **Quality**: ruff for linting/formatting, CI on every push/PR.
- **Containerized**: `Dockerfile` + `docker-compose.yml` (app + Postgres), with a named volume
  for the Postgres data directory.

## Tech Stack

| Layer | Choice |
|---|---|
| Language | Python 3.13 |
| Framework | FastAPI (async) |
| Database | PostgreSQL, Alembic migrations |
| ORM | SQLAlchemy 2.0 (async, `asyncpg`) |
| Auth | PyJWT (JWT access tokens) + DB-backed refresh tokens, argon2 password hashing |
| Testing | pytest, pytest-asyncio, `TestClient`, in-memory SQLite for unit tests |
| Observability | `prometheus_client`, per-request trace IDs, loguru structured logging |
| Config | Dynaconf (`configs/config.yaml` + `.env`) |
| Lint | ruff |
| CI | GitHub Actions |

## Using This as a Template

1. Clone this repository (or use it as a starting point for a new one — there's no GitHub
   "template repository" flag to click here, just `git clone` and re-init `.git` yourself).
2. Rename the project: run `./actions/init-project.sh orders` (or
   `.\actions\init-project.ps1 -NewName orders` on Windows). This updates everything derived
   from the project name — `app.name` in `configs/config.yaml`, the `logs/*.log` file name, the
   default `DB_NAME`/`POSTGRES_DB` in `.env.example`, and the Postgres data volume name in
   `docker-compose.yml`. Review the diff, then delete both scripts under `actions/` once you're
   happy with the result.
3. Copy `src/.env.example` to `src/.env` and fill in real values — it's git-ignored, so nothing
   you put there gets committed. See [Configuration](#configuration) below.
4. Create the database: the bundled `docker-compose.yml` Postgres service creates whatever
   database `POSTGRES_DB` names automatically on first boot of a fresh volume (this is the
   official `postgres` image's built-in behavior — no extra script needed). For any other setup
   (local Postgres, an already-initialized volume, a remote database), create the database
   named by `DB_NAME` yourself before starting the app.
5. Replace `src/alembic/versions/0001_initial_schema.py` with your own schema, or add new
   revisions on top of it with `alembic revision --autogenerate -m "..."` (run from `src/`).
6. Swap out the `User`/`Auth` domain for your own entities, or build alongside it — the
   `infrastructure` (models/repositories/unit-of-work) / `services` / `api` package split is
   meant to generalize.

## Repository Map

```
.
├── Dockerfile                    App image (python:3.13-alpine, installs requirements.txt)
├── docker-compose.yml            App + Postgres for local/full-stack runs
├── actions/
│   ├── init-project.sh           Rename script (bash) — delete after use
│   ├── init-project.ps1          Rename script (PowerShell) — delete after use
│   └── export_openapi.py         Regenerates docs/api-docs.json from the live app
├── docs/
│   └── api-docs.json             Exported OpenAPI spec for this project
├── .github/workflows/ci.yml      CI: ruff check + pytest on push & PR
└── src/
    ├── .env.example               Template for local secrets/config (copy to .env)
    ├── entrypoint.sh              Container entrypoint: waits for Postgres, runs alembic, starts uvicorn
    ├── alembic/                   Alembic env + versioned migrations
    ├── configs/config.yaml        Base app config (env-var driven via Dynaconf)
    ├── app/
    │   ├── main.py                FastAPI app factory, lifespan (admin bootstrap), middleware
    │   ├── run.py                 Local dev entry point (uvicorn)
    │   ├── actions/                Startup actions (admin bootstrap) + standalone reseed script
    │   ├── api/
    │   │   ├── v1/endpoints/       Auth, Users, Health, Metrics routers
    │   │   ├── v1/dependencies/     Current-user / admin / admin-or-self / pagination / filter deps
    │   │   ├── v1/exceptions/       API-facing exception classes, domain->API error mapping, handlers
    │   │   └── v1/utils/            Refresh-token cookie helpers
    │   ├── core/
    │   │   ├── config.py           Dynaconf settings
    │   │   ├── schemas/             Request/response Pydantic models (camelCase)
    │   │   ├── exceptions/          Domain exception hierarchy
    │   │   ├── middleware/          X-Trace-Id middleware
    │   │   └── utils/               Password/duration/pagination/datetime helpers
    │   ├── infrastructure/
    │   │   ├── models/               SQLAlchemy entities (User, RefreshToken)
    │   │   ├── repositories/         Data-access layer
    │   │   ├── unit_of_work/         Transaction boundary wrapping the repositories
    │   │   └── database/             Async engine/session factory
    │   └── services/                 Business logic (AuthService, UserService, JWTService)
    └── tests/                       pytest suite (in-memory SQLite; see Common Commands)
```

## Configuration

The app is configured entirely through environment variables (see `configs/config.yaml` for
defaults); a local `src/.env` (git-ignored) supplies real values for both direct `uvicorn` runs
and `docker-compose.yml`:

| Variable | Purpose |
|---|---|
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | Postgres connection |
| `APP_SECURITY_JWT_SECRET` | Secret used to sign JWT access/refresh tokens |
| `APP_SECURITY_ACCESS_TOKEN_EXPIRATION` | Access token TTL (default `15m`) |
| `APP_SECURITY_REFRESH_TOKEN_EXPIRATION` | Refresh token TTL (default `30d`) |
| `APP_ADMIN_EMAIL`, `APP_ADMIN_PASSWORD`, `APP_ADMIN_FULLNAME` | Bootstrap admin account, created automatically on every startup if it doesn't exist yet |
| `APP_CORS_ALLOWED_ORIGINS` | Comma-separated list of allowed CORS origins (default `http://localhost,http://localhost:8080`) |
| `APP_COOKIE_SECURE` | Whether the refresh-token cookie gets the `Secure` attribute (default `true`). Set to `false` for local/HTTP-only dev — browsers silently drop `Secure` cookies over plain HTTP, which otherwise looks like login "not persisting". |
| `CONFIG_PATH` | Path to `config.yaml` inside the container (leave as-is for local/dev use) |
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | Credentials `docker-compose.yml`'s Postgres service boots with |

Running the unit-test suite does **not** require Docker or a running Postgres — tests use an
in-memory SQLite database via fixtures in `tests/conftest.py`. It does require a populated
`src/.env` (Dynaconf reads it at import time).

File logs are written to `logs/app.log` (renamed by `actions/init-project.sh`, rotated at 10MB,
kept 10 days, gzip-compressed) under `src/`.

## Common Commands

Run everything from the `src/` directory unless noted otherwise.

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app locally (needs a reachable Postgres + a populated .env)
python -m app.run

# Apply database migrations
alembic upgrade head

# Run the test suite (in-memory SQLite, no Docker required)
python -m pytest

# Run one test file or test
python -m pytest tests/test_auth_endpoints.py -v
python -m pytest tests/test_auth_endpoints.py::test_login_returns_200_and_sets_refresh_cookie -v

# Check formatting/lint
ruff check .

# Auto-fix formatting issues
ruff check . --fix

# Run the full stack (app + Postgres) in Docker, from the repo root
docker compose up --build
```

## API Overview

Base path: `/api/v1`.

- `POST /auth/register` — create an account, returns access token + sets refresh-token cookie
- `POST /auth/login` — authenticate, returns access token + sets refresh-token cookie
- `POST /auth/refresh` — rotate the refresh token, returns a new access token
- `POST /auth/logout` — revoke the current refresh token
- `GET /users` — list users, paginated/filterable (admin only)
- `POST /users` — create a user (admin only)
- `GET /users/me`, `PUT /users/me` — read/update the current user
- `GET /users/{id}`, `PUT /users/{id}`, `DELETE /users/{id}` — admin, or self for GET/PUT
- `GET /health/liveness` — always 200
- `GET /health/readiness` — 200 if the database is reachable, else 503 with `checks`
- `GET /metrics` — Prometheus exposition format

Interactive docs are served by FastAPI once the app is running (Swagger UI at `/docs`); a static
export of this project's spec lives in `docs/api-docs.json` (regenerate it with
`python actions/export_openapi.py` from the repo root after changing any endpoint or schema).

Every response carries an `X-Trace-Id` header; on errors, the same value is embedded as
`traceId` in the `ErrorResponse` body, so a report from a client can be matched to server-side
log lines for that request.

## CI

`.github/workflows/ci.yml` runs on every push and PR to `main`: `ruff check` and `pytest`. See
that workflow file for exactly what runs — this section is intentionally short so it can't drift
out of sync with the real CI config.

## License

MIT License — see [LICENSE](../LICENSE).
````

- [ ] **Step 2: Sanity-check the doc against the actual repo**

Run these from the repo root and confirm nothing in the README references a path, command, or
env var that doesn't exist:

```bash
grep -c "app.name" src/configs/config.yaml   # expect: config.yaml has an `app:`/`name:` pair
grep "APP_ADMIN_EMAIL\|APP_CORS_ALLOWED_ORIGINS" src/.env.example   # expect: both present (Stage 3)
```

If either check fails, Stage 3 wasn't fully applied yet — stop and finish it before continuing.

- [ ] **Step 3: Commit**

```bash
git add src/README.md
git commit -m "docs: write src/README.md as a real template document"
```

---

### Task 2: `actions/init-project.sh` + `actions/init-project.ps1`

One-command rename, matching Kotlin's `actions/init-project.sh`/`.ps1`. Scope is deliberately
narrower than Kotlin's package rename (Python has no equivalent of renaming a Java package) —
it renames the things that are actually specific to this project: the display name in
`configs/config.yaml`, the log file name, the default DB name in `.env.example`, and the
Postgres volume name in `docker-compose.yml`.

**Files:**
- Create: `actions/init-project.sh`
- Create: `actions/init-project.ps1`
- Test: `src/tests/test_init_project_script.py`

**Interfaces:** None — standalone scripts, not imported by app code.

- [ ] **Step 1: Write the failing test**

Create `src/tests/test_init_project_script.py`:

```python
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _fixture_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "src" / "configs").mkdir(parents=True)
    (repo / "actions").mkdir()

    shutil.copy(REPO_ROOT / "src" / "configs" / "config.yaml", repo / "src" / "configs" / "config.yaml")
    shutil.copy(REPO_ROOT / "src" / ".env.example", repo / "src" / ".env.example")
    shutil.copy(REPO_ROOT / "docker-compose.yml", repo / "docker-compose.yml")
    shutil.copy(REPO_ROOT / "actions" / "init-project.sh", repo / "actions" / "init-project.sh")

    return repo


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available on this machine")
def test_init_project_sh_renames_app_name_slug_db_and_volume(tmp_path):
    repo = _fixture_repo(tmp_path)

    result = subprocess.run(
        ["bash", str(repo / "actions" / "init-project.sh"), "Orders"],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    config_text = (repo / "src" / "configs" / "config.yaml").read_text(encoding="utf-8")
    assert "name: Orders" in config_text
    assert "path: logs/orders.log" in config_text

    env_text = (repo / "src" / ".env.example").read_text(encoding="utf-8")
    assert "DB_NAME=orders" in env_text
    assert "POSTGRES_DB=orders" in env_text

    compose_text = (repo / "docker-compose.yml").read_text(encoding="utf-8")
    assert "orders_db_data:" in compose_text
    assert "- orders_db_data:/var/lib/postgresql/data" in compose_text


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash not available on this machine")
def test_init_project_sh_requires_exactly_one_argument(tmp_path):
    repo = _fixture_repo(tmp_path)

    result = subprocess.run(
        ["bash", str(repo / "actions" / "init-project.sh")],
        cwd=repo,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd src && python -m pytest tests/test_init_project_script.py -v`
Expected: FAIL — `actions/init-project.sh` doesn't exist yet (`shutil.copy` raises `FileNotFoundError` inside `_fixture_repo`).

- [ ] **Step 3: Write `actions/init-project.sh`**

Create `actions/init-project.sh`:

```sh
#!/bin/sh
set -e

usage() {
  echo "Usage: ./actions/init-project.sh <new-app-name>"
  echo "  e.g. ./actions/init-project.sh Orders"
  echo "  Renames app.name in configs/config.yaml, the log file name, the default"
  echo "  DB_NAME/POSTGRES_DB in .env.example, and the Postgres volume name in"
  echo "  docker-compose.yml. Does not touch your local .env (git-ignored) or rename"
  echo "  any Python package/module."
  exit 1
}

[ $# -eq 1 ] || usage
NEW_NAME="$1"
SLUG=$(echo "$NEW_NAME" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9' '-' | sed 's/-\{2,\}/-/g; s/^-//; s/-$//')

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

echo "[init-project] app.name -> '${NEW_NAME}', slug -> '${SLUG}'"

sed -i.bak "s/^  name: .*/  name: ${NEW_NAME}/" "${REPO_ROOT}/src/configs/config.yaml"
sed -i.bak "s#path: logs/app\.log#path: logs/${SLUG}.log#" "${REPO_ROOT}/src/configs/config.yaml"
sed -i.bak "s/^DB_NAME=.*/DB_NAME=${SLUG}/" "${REPO_ROOT}/src/.env.example"
sed -i.bak "s/^POSTGRES_DB=.*/POSTGRES_DB=${SLUG}/" "${REPO_ROOT}/src/.env.example"
sed -i.bak "s/db_data:/${SLUG}_db_data:/g" "${REPO_ROOT}/docker-compose.yml"

find "${REPO_ROOT}/src/configs" "${REPO_ROOT}/src" "${REPO_ROOT}" -maxdepth 1 -name "*.bak" -delete

echo "[init-project] Done. Review the diff (git diff), then:"
echo "  1. Copy src/.env.example to src/.env and fill in real secrets."
echo "  2. Delete this script and actions/init-project.ps1 once you're happy with the result."
echo "  3. Run the test suite: cd src && python -m pytest"
```

Make it executable: `chmod +x actions/init-project.sh`

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd src && python -m pytest tests/test_init_project_script.py -v`
Expected: PASS.

- [ ] **Step 5: Write `actions/init-project.ps1` (the Windows equivalent)**

Create `actions/init-project.ps1`:

```powershell
param(
    [Parameter(Mandatory = $true)]
    [string]$NewName
)

$RepoRoot = Split-Path -Parent $PSScriptRoot
$Slug = ($NewName.ToLower() -replace '[^a-z0-9]+', '-').Trim('-')

Write-Host "[init-project] app.name -> '$NewName', slug -> '$Slug'"

$configPath = Join-Path $RepoRoot "src\configs\config.yaml"
(Get-Content $configPath) `
    -replace '^  name: .*', "  name: $NewName" `
    -replace 'path: logs/app\.log', "path: logs/$Slug.log" |
    Set-Content -Encoding utf8 $configPath

$envExamplePath = Join-Path $RepoRoot "src\.env.example"
(Get-Content $envExamplePath) `
    -replace '^DB_NAME=.*', "DB_NAME=$Slug" `
    -replace '^POSTGRES_DB=.*', "POSTGRES_DB=$Slug" |
    Set-Content -Encoding utf8 $envExamplePath

$composePath = Join-Path $RepoRoot "docker-compose.yml"
(Get-Content $composePath) -replace 'db_data:', "${Slug}_db_data:" |
    Set-Content -Encoding utf8 $composePath

Write-Host "[init-project] Done. Review the diff (git diff), then:"
Write-Host "  1. Copy src\.env.example to src\.env and fill in real secrets."
Write-Host "  2. Delete this script and actions/init-project.sh once you're happy with the result."
Write-Host "  3. Run the test suite: cd src; python -m pytest"
```

- [ ] **Step 6: Manually verify the PowerShell script**

There's no automated test for the `.ps1` variant (GitHub Actions' `ubuntu-latest` runner used
in Stage 5's CI won't have it exercised, and a Linux dev machine may not have `pwsh`). Verify it
by hand once, from the repo root, against a scratch copy — do **not** run it against the real
repo files:

```powershell
Copy-Item -Recurse . "$env:TEMP\fish-init-test" -Exclude ".git"
& "$env:TEMP\fish-init-test\actions\init-project.ps1" -NewName Orders
Get-Content "$env:TEMP\fish-init-test\src\configs\config.yaml" | Select-String "name: Orders"
Get-Content "$env:TEMP\fish-init-test\src\.env.example" | Select-String "DB_NAME=orders"
Get-Content "$env:TEMP\fish-init-test\docker-compose.yml" | Select-String "orders_db_data"
Remove-Item -Recurse -Force "$env:TEMP\fish-init-test"
```

Confirm all three `Select-String` calls print a match before moving on.

- [ ] **Step 7: Run the full pytest suite**

Run: `cd src && python -m pytest -v`
Expected: all PASS.

- [ ] **Step 8: Commit**

```bash
git add actions/init-project.sh actions/init-project.ps1 src/tests/test_init_project_script.py
git commit -m "feat: add init-project rename scripts for forking this template"
```

---

### Task 3: OpenAPI export script (`docs/api-docs.json`)

Kotlin ships a static `docs/api-docs.json` export of its OpenAPI spec. This adds the FastAPI
equivalent: a script that imports the live `app` object and dumps `app.openapi()`.

**Files:**
- Create: `actions/export_openapi.py`
- Create: `docs/api-docs.json` (generated by running the script — commit the output)
- Test: `src/tests/test_init_project_script.py` (add to the same file — it's about the `actions/`
  scripts as a group)

- [ ] **Step 1: Write the failing test**

Add to `src/tests/test_init_project_script.py`:

```python
import json
import sys


def test_export_openapi_writes_valid_spec_with_known_routes(tmp_path):
    output_path = tmp_path / "api-docs.json"

    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "actions" / "export_openapi.py"), "--out", str(output_path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    spec = json.loads(output_path.read_text(encoding="utf-8"))
    assert spec["info"]["title"]
    assert "/api/v1/auth/register" in spec["paths"]
    assert "/api/v1/users/{user_id}" in spec["paths"]
```

(This test runs the script against a `tmp_path` output file rather than the real
`docs/api-docs.json`, via the `--out` flag added in Step 3, so it doesn't depend on run order or
leave the repo dirty.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd src && python -m pytest tests/test_init_project_script.py::test_export_openapi_writes_valid_spec_with_known_routes -v`
Expected: FAIL — `actions/export_openapi.py` doesn't exist yet.

- [ ] **Step 3: Write the script**

Create `actions/export_openapi.py`:

```python
import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Export this project's OpenAPI schema to a JSON file.")
    parser.add_argument(
        "--out",
        type=Path,
        default=REPO_ROOT / "docs" / "api-docs.json",
        help="Output path (default: docs/api-docs.json)",
    )
    args = parser.parse_args()

    from app.main import app

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(app.openapi(), indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote OpenAPI spec to {args.out}")


if __name__ == "__main__":
    main()
```

(Needs `src/.env` populated, same as any other script that imports `app.main` — Dynaconf reads
it at import time.)

- [ ] **Step 4: Run test to verify it passes**

Run: `cd src && python -m pytest tests/test_init_project_script.py -v`
Expected: PASS.

- [ ] **Step 5: Generate the real `docs/api-docs.json`**

Run from the repo root: `python actions/export_openapi.py`
Expected output: `Wrote OpenAPI spec to <repo-root>/docs/api-docs.json`

- [ ] **Step 6: Run the full pytest suite**

Run: `cd src && python -m pytest -v`
Expected: all PASS.

- [ ] **Step 7: Commit**

```bash
git add actions/export_openapi.py docs/api-docs.json src/tests/test_init_project_script.py
git commit -m "feat: add OpenAPI export script and commit docs/api-docs.json"
```

---

## After this plan

`FastAPI-Fish` now matches Kotlin's fork workflow: clone, run one rename script, copy `.env`,
`docker compose up`. One stage remains:

- **Stage 5 — Tests & CI**: add real-Postgres integration tests (today's suite is SQLite-only)
  and `.github/workflows/ci.yml`. Once that lands, Stage 5 should also update `src/README.md`'s
  CI section if the actual workflow ends up doing anything beyond "ruff check + pytest" (e.g. a
  Postgres service container) — keep the doc and the workflow file in sync.
