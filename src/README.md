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

Apache License 2.0 — see [LICENSE](../LICENSE).
