#!/usr/bin/env bash
# API and database checks for a PR worktree made by review-worktree.sh.
# Uses a throwaway pgvector database and a throwaway virtualenv.
#   - Docker must be local (no remote context or DOCKER_HOST).
#   - Docker picks a free port on 127.0.0.1; Alembic and pytest use the URL built
#     from that container's port, so the downgrade only touches this review's database.
#   - Never uses the dev database or any .env file.
#   - Removes only the container it created, always.
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

report_header

# True when Docker talks to this machine (a local socket or Windows named pipe).
docker_is_local() {
  local endpoint
  if [[ -n "${DOCKER_HOST:-}" ]]; then
    endpoint="$DOCKER_HOST"
  else
    endpoint="$(docker context inspect --format '{{.Endpoints.docker.Host}}' 2>/dev/null)" || return 1
  fi
  [[ "$endpoint" == unix://* || "$endpoint" == npipe://* ]]
}

# Prints the host port Docker gave to the container's 5432, e.g. 49153.
published_port() {
  docker port "$1" 5432/tcp 2>/dev/null | grep -m1 '^127\.0\.0\.1:' | cut -d: -f2
}

if ! command -v docker >/dev/null 2>&1; then
  not_run "database" "docker run pgvector/pgvector:pg16" "Docker is not installed"
  exit 1
fi
if ! docker_is_local; then
  not_run "database" "docker run pgvector/pgvector:pg16" "Docker is not local (remote context or DOCKER_HOST); reviews only use a local throwaway database"
  exit 1
fi

container=""
venv="$(mktemp -d -t edugest-review-venv-XXXX)"
cleanup() {
  if [[ -n "$container" ]]; then
    docker rm --force "$container" >/dev/null 2>&1 || true
  fi
  rm -rf "$venv"
}
trap cleanup EXIT

# Port 0 on 127.0.0.1: Docker chooses a free port, reachable only from this machine.
container="$(docker run --detach --rm --name "edugest-review-db-$$" \
  -e POSTGRES_USER=review -e POSTGRES_PASSWORD=review -e POSTGRES_DB=gistar_review \
  -p 127.0.0.1::5432 pgvector/pgvector:pg16)" || {
  container=""
  not_run "database" "docker run pgvector/pgvector:pg16" "the container did not start"
  exit 1
}

port="$(published_port "$container")"
if [[ -z "$port" ]]; then
  not_run "database" "docker port $container 5432/tcp" "could not read the port Docker assigned"
  exit 1
fi

ready=0
for _ in $(seq 1 30); do
  if docker exec "$container" pg_isready -U review -d gistar_review >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done
if [[ "$ready" -eq 0 ]]; then
  not_run "database" "pg_isready" "the review database was not ready after 30 seconds"
  exit 1
fi

db_url="postgresql+psycopg://review:review@127.0.0.1:$port/gistar_review"
echo "Review database: 127.0.0.1:$port (container ${container:0:12}, removed on exit)"

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
