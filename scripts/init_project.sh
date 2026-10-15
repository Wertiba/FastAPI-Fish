#!/bin/sh
# Переименовать шаблон под свой проект:  ./scripts/init_project.sh "My Hackathon"
# Меняет: имя в pyproject.toml (+ uv lock), DB_NAME / POSTGRES_DB в .env.example,
# имя тома Postgres в docker-compose.yml. Пакет `app` не трогает.
set -e

[ $# -eq 1 ] || { echo "Usage: $0 <project-name>"; exit 1; }
NAME="$1"
SLUG=$(echo "$NAME" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9\n' '-' | sed 's/-\{2,\}/-/g; s/^-//; s/-$//')
DB=$(echo "$SLUG" | tr '-' '_')
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

sed -i.bak "s/^name = \".*\"/name = \"${SLUG}\"/" "$ROOT/pyproject.toml"
sed -i.bak "s/^DB_NAME=.*/DB_NAME=${DB}/; s/^POSTGRES_DB=.*/POSTGRES_DB=${DB}/" "$ROOT/.env.example"
sed -i.bak "s/\bdb_data\b/${DB}_db_data/g" "$ROOT/docker-compose.yml"
rm -f "$ROOT"/*.bak

# имя проекта записано и в uv.lock — без перегенерации `uv sync --locked` упадёт
(cd "$ROOT" && uv lock)

echo "Готово: ${NAME} (slug=${SLUG}, db=${DB}). Дальше:"
echo "  cp .env.example .env   # и поменяйте секреты"
echo "  git diff               # проверьте изменения"
