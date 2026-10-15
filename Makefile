.PHONY: install run test test-pg lint fmt typecheck check migrate migration module openapi lock up down

install:            ## окружение .venv со всеми зависимостями (включая dev)
	uv sync

run:                ## локальный запуск с autoreload (нужен .env и Postgres)
	uv run python -m app

test:               ## тесты на in-memory SQLite
	uv run pytest

test-pg:            ## те же тесты на PostgreSQL: make test-pg DB=postgresql+asyncpg://...
	TEST_DB_URL=$(DB) uv run pytest

lint:
	uv run ruff check .
	uv run ruff format --check .

fmt:
	uv run ruff check --fix .
	uv run ruff format .

typecheck:
	uv run mypy

check: lint typecheck test

migrate:            ## применить миграции
	uv run alembic upgrade head

migration:          ## make migration m="add projects"
	uv run alembic revision --autogenerate -m "$(m)"

module:             ## make module name=projects [entity=Project]
	uv run python scripts/new_module.py $(name) $(entity)

openapi:
	uv run python scripts/export_openapi.py

lock:               ## обновить uv.lock после правки зависимостей
	uv lock

up:
	docker compose up --build -d

down:
	docker compose down
