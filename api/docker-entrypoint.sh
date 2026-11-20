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
# Ingesta del RAG (KAN-130): repetible y sin datos personales. Nunca bloquea el arranque: si falla, rechaza un
# documento o tarda más de 3 minutos (p. ej. Gemini no responde), la API arranca con el conocimiento que ya había
# y el aviso queda en el log. Los vectores solo se generan con GISTAR_RAG_EMBED=true y GEMINI_API_KEY.
timeout 180 python -m app.modules.knowledge.ingest \
  || echo "Aviso: la ingesta del RAG no ha terminado bien; la API arranca con el conocimiento que ya había." >&2
# --no-access-log: el log de acceso de uvicorn imprime la ruta cruda y la query string (datos personales). La API
# escribe su propio log seguro (app.access).
exec uvicorn app.main:app --no-access-log --host 0.0.0.0 --port "${PORT:-8000}"
