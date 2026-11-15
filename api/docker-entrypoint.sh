#!/bin/sh
# Arranque del contenedor: migraciones, semilla sintética idempotente y servidor.
set -eu

# Render entrega DATABASE_URL como postgresql://...; la API usa el driver psycopg 3.
if [ -z "${GISTAR_DATABASE_URL:-}" ] && [ -n "${DATABASE_URL:-}" ]; then
  GISTAR_DATABASE_URL="postgresql+psycopg://${DATABASE_URL#*://}"
  export GISTAR_DATABASE_URL
fi

alembic upgrade head
python -m app.seed
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
