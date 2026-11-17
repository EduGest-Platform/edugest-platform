#!/usr/bin/env bash
# Comprobación de humo del compose (evidencia de YO1). Uso, tras `docker compose -f infra/compose.yaml up -d --build --wait`:
#   bash infra/smoke-test.sh
# Variables opcionales: API_URL, WEB_URL, MLFLOW_URL.
# La contraseña de las cuentas sintéticas sale de DEMO_PASSWORD o, si no está, de GISTAR_DEMO_PASSWORD en infra/.env.
set -u
API_URL="${API_URL:-http://127.0.0.1:8000}"
WEB_URL="${WEB_URL:-http://127.0.0.1:8443}"
MLFLOW_URL="${MLFLOW_URL:-http://127.0.0.1:5000}"
ENV_FILE="$(cd "$(dirname "$0")" && pwd)/.env"

if [ -z "${DEMO_PASSWORD:-}" ] && [ -f "$ENV_FILE" ]; then
  DEMO_PASSWORD="$(grep '^GISTAR_DEMO_PASSWORD=' "$ENV_FILE" | head -n 1 | cut -d= -f2- | tr -d '\r')"
fi
if [ -z "${DEMO_PASSWORD:-}" ]; then
  echo "Falta la contraseña demo: define DEMO_PASSWORD o GISTAR_DEMO_PASSWORD en infra/.env" >&2
  exit 2
fi
fail=0

check() { # nombre, comando...
  local name="$1"; shift
  if "$@" >/dev/null 2>&1; then echo "PASS  $name"; else echo "FAIL  $name"; fail=1; fi
}

echo "# smoke-test $(date -u +%Y-%m-%dT%H:%M:%SZ)"
check "API /health (api + base de datos)" curl -fsS "$API_URL/health"
check "API /docs" curl -fsS "$API_URL/docs"
check "Web sirve index.html" curl -fsS "$WEB_URL/"
check "Web: ruta de la SPA devuelve index.html" curl -fsS "$WEB_URL/candidaturas"
check "MLflow /health" curl -fsS "$MLFLOW_URL/health"
check "Login sintético (admin)" curl -fsS -X POST "$API_URL/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"admin@gistar.example\",\"password\":\"$DEMO_PASSWORD\"}"

[ "$fail" -eq 0 ] && echo "RESULTADO: todo en verde" || echo "RESULTADO: hay fallos"
exit "$fail"
