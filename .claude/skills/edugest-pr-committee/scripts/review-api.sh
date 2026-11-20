#!/usr/bin/env bash
# API and database checks for a PR worktree made by review-worktree.sh.
# Uses a throwaway pgvector database on port 55432 and a throwaway virtualenv.
# Never uses the dev database or any .env file. The container is always removed.
# Usage: review-api.sh <worktree>
set -uo pipefail
worktree="${1:?Give the worktree path printed by review-worktree.sh}"
source "$(dirname "$0")/report.sh"
cd "$worktree/api" || exit 1

if [[ -e .env || -e ../.env || -e ../infra/.env ]]; then
  echo "This worktree has a .env file. Remove it: reviews never use real settings." >&2
  exit 1
fi

# Only synthetic, local settings. Clear anything inherited from your shell.
unset GISTAR_DATABASE_URL GISTAR_TEST_DATABASE_URL
db_url="postgresql+psycopg://review:review@localhost:55432/gistar_review"

report_header

if ! command -v docker >/dev/null 2>&1; then
  not_run "database" "docker run pgvector/pgvector:pg16" "Docker is not installed"
  exit 1
fi

container="edugest-review-db-$$"
venv="$(mktemp -d -t edugest-review-venv-XXXX)"
cleanup() {
  docker rm --force "$container" >/dev/null 2>&1 || true
  rm -rf "$venv"
}
trap cleanup EXIT

docker run --detach --rm --name "$container" \
  -e POSTGRES_USER=review -e POSTGRES_PASSWORD=review -e POSTGRES_DB=gistar_review \
  -p 55432:5432 pgvector/pgvector:pg16 >/dev/null || {
  not_run "database" "docker run pgvector/pgvector:pg16" "the container did not start (is port 55432 free?)"
  exit 1
}
for _ in $(seq 1 30); do
  docker exec "$container" pg_isready -U review -d gistar_review >/dev/null 2>&1 && break
  sleep 1
done

python3 -m venv "$venv"
# shellcheck disable=SC1091
source "$venv/bin/activate"
run_check "install" "pip install --quiet -e '.[dev]'"

if command -v ruff >/dev/null 2>&1; then
  run_check "lint" "ruff check ."
else
  not_run "lint" "ruff check ." "ruff is not in this branch's dev dependencies"
fi

export GISTAR_DATABASE_URL="$db_url" GISTAR_TEST_DATABASE_URL="$db_url"
run_check "migrations" "alembic upgrade head && alembic check && alembic downgrade base && alembic upgrade head"
run_check "tests" "pytest -q"

echo
echo "Logs: $LOG_DIR (the database container and virtualenv are removed on exit)"
exit "$FAILED"
