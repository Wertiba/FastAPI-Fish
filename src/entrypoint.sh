#!/bin/sh
set -e

# DB_URL: jdbc:postgresql://host:5432/db or postgresql://[user:pass@]host:5432/db
if [ -n "${DB_URL:-}" ]; then
  _hostport="${DB_URL#*://}"    # strip scheme
  _hostport="${_hostport%%/*}"  # strip /dbname?params
  _hostport="${_hostport##*@}"  # strip user:pass@
  DB_WAIT_HOST="${_hostport%%:*}"
  case "$_hostport" in
    *:*) DB_WAIT_PORT="${_hostport##*:}" ;;
    *)   DB_WAIT_PORT=5432 ;;
  esac

  echo "[entrypoint] Waiting for Postgres at ${DB_WAIT_HOST}:${DB_WAIT_PORT} ..."
  until pg_isready -h "${DB_WAIT_HOST}" -p "${DB_WAIT_PORT}" -U "${DB_USER:-postgres}" >/dev/null 2>&1; do
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

echo "[entrypoint] Starting application..."
exec "$@"
