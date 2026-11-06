.PHONY: install run run-api run-worker run-scheduler run-bot infra test test-pg lint fmt typecheck check migrate migration migration-sql module domain openapi lock up down

install:            ## окружение .venv со всеми зависимостями (включая dev)
	uv sync

run: run-api        ## локальный запуск API (нужны src/.env и Postgres)

run-api:            ## FastAPI: сайт и мобильное приложение
	uv run --env-file src/.env python -m app.run api

run-worker:         ## outbox relay + консьюмеры (Kafka или локально)
	uv run --env-file src/.env python -m app.run worker

run-scheduler:      ## периодические задачи модулей
	uv run --env-file src/.env python -m app.run scheduler

run-bot:            ## Telegram long polling (нужен TELEGRAM_BOT_TOKEN)
	uv run --env-file src/.env python -m app.run bot

infra:              ## только инфраструктура в Docker (Postgres, Redis, Kafka, MinIO), процессы запускайте локально
	docker compose up -d db redis kafka minio minio-bucket

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

migration:          ## автогенерация по tables.py: make migration m="add projects"
	uv run --env-file src/.env alembic -c src/alembic.ini revision --autogenerate -m "$(m)"

migration-sql:      ## миграция на чистом SQL (.up.sql / .down.sql): make migration-sql m="add projects"
	uv run python scripts/new_sql_migration.py "$(m)"

module:             ## make module name=projects [entity=Project]
	uv run python scripts/new_module.py $(name) $(entity)

domain: module      ## старое имя make module

openapi:            ## обновить docs/openapi.json
	uv run python scripts/export_openapi.py

lock:               ## обновить uv.lock после правки зависимостей
	uv lock

up:
	docker compose up --build -d

down:
	docker compose down
