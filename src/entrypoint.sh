#!/bin/sh
set -e

echo "[entrypoint] ENV DB_HOST=${DB_HOST:-} DB_PORT=${DB_PORT:-5432} DB_USER=${DB_USER:-} DB_NAME=${DB_NAME:-}"

if [ -n "${DB_HOST:-}" ]; then
  echo "[entrypoint] Waiting for Postgres at ${DB_HOST}:${DB_PORT:-5432} ..."
  until pg_isready -h "${DB_HOST}" -p "${DB_PORT:-5432}" -U "${DB_USER:-postgres}" >/dev/null 2>&1; do
    printf '.'
    sleep 1
  done
  echo ""
  echo "[entrypoint] Postgres is available"
fi

if command -v alembic >/dev/null 2>&1; then
  echo "[entrypoint] Running alembic upgrade head..."
  alembic upgrade head
else
  echo "[entrypoint] alembic not found in PATH — skipping migrations"
fi

echo "[entrypoint] Creating first admin if not exists..."
python -m app.actions.run

echo "[entrypoint] Starting application..."
exec "$@"
