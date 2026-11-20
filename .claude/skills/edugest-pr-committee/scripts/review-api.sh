#!/usr/bin/env bash
set -euo pipefail

# Run from the root of the detached review worktree with its own Python environment active.
endpoint=${DOCKER_HOST:-}
if [[ -z "$endpoint" || -n "${DOCKER_CONTEXT:-}" ]]; then
  endpoint=$(docker context inspect --format '{{.Endpoints.docker.Host}}')
fi
case "$endpoint" in
  unix:///*|npipe:////./pipe/*) ;;
  *) echo 'Use a local Docker context for the disposable database.' >&2; exit 2 ;;
esac

container=$(docker run --rm -d -p 127.0.0.1::5432 -e POSTGRES_USER=review \
  -e POSTGRES_PASSWORD=review-synthetic-only -e POSTGRES_DB=review pgvector/pgvector:pg16)
trap 'docker stop "$container" >/dev/null 2>&1 || true' EXIT
ready=false
for ((attempt = 0; attempt < 30; attempt++)); do
  if docker exec "$container" pg_isready -h 127.0.0.1 -U review -d review >/dev/null 2>&1; then
    ready=true
    break
  fi
  sleep 1
done
if [[ "$ready" != true ]]; then
  echo 'The disposable review database did not become ready.' >&2
  exit 1
fi
port=$(docker port "$container" 5432/tcp)
export GISTAR_ENVIRONMENT=local
export GISTAR_DATABASE_URL="postgresql+psycopg://review:review-synthetic-only@${port}/review"
export GISTAR_TEST_DATABASE_URL="$GISTAR_DATABASE_URL"
cd api
python -m ruff check . --select E4,E7,E9,F
python -m alembic upgrade head
python -m alembic check
python -m alembic downgrade base
python -m alembic upgrade head
python -m pytest
