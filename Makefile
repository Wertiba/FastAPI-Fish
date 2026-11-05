.PHONY: install run test test-pg lint fmt typecheck check migrate migration domain openapi lock up down

install:            ## окружение .venv со всеми зависимостями (включая dev)
	uv sync

run:                ## локальный запуск (нужны src/.env и Postgres)
	uv run --env-file src/.env python -m app.run

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
	uv run --env-file src/.env alembic -c src/alembic.ini upgrade head

migration:          ## make migration m="add projects"
	uv run --env-file src/.env alembic -c src/alembic.ini revision --autogenerate -m "$(m)"

domain:             ## make domain name=projects [entity=Project]
	uv run python scripts/new_domain.py $(name) $(entity)

openapi:            ## обновить docs/openapi.json
	uv run python scripts/export_openapi.py

lock:               ## обновить uv.lock после правки зависимостей
	uv lock

up:
	docker compose up --build -d

down:
	docker compose down
