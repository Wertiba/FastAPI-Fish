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
