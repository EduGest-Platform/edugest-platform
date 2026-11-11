# Gistar API (nombre provisional)

FastAPI + SQLAlchemy 2 + Alembic sobre **PostgreSQL** (nunca SQLite: las pruebas usan la misma base que producción).
Datos **exclusivamente sintéticos**. La autorización se comprueba en el servidor por **rol + ámbito**.

## Arranque local

```bash
cd api
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env              # pon la contraseña de infra/.env en GISTAR_DATABASE_URL (ver infra/.env.example)
alembic upgrade head
python -m app.seed                # carga ../src/gistar/seed.json (idempotente; --reset para recargar)
uvicorn app.main:app --reload     # http://localhost:8000/docs
```

Web contra la API (desde la raíz): `VITE_GISTAR_API_URL=http://localhost:8000 pnpm dev`.
Alternativa con contenedores: `docker compose -f infra/compose.yaml up --build` (validado 11/11/2026; requiere `infra/.env`, ver `infra/.env.example`). El contenedor aplica migraciones y seed idempotente al arrancar; los puertos 5432 y 8000 se publican solo en `127.0.0.1`.

## Pruebas

```bash
# GISTAR_TEST_DATABASE_URL está en api/.env (git-ignorado); bash la carga así:
export $(grep GISTAR_TEST_DATABASE_URL .env) && pytest
```

En PowerShell: lee la variable de `api/.env` y expórtala antes de `pytest` (sin imprimirla).

La base de pruebas se migra de `base` a `head` en cada sesión y se vacía y re-siembra en cada test.

## Contrato

`python scripts/export_openapi.py` → `contracts/openapi.json`; después `pnpm gen:api` en la raíz para regenerar
`src/shared/api/schema.gen.ts`. `tests/test_contract.py` falla si el contrato versionado no coincide con la API.

## Cuentas sintéticas (contraseña: `GISTAR_DEMO_PASSWORD`, por defecto `gistar-demo-2026`)

| Cuenta | Rol · ámbito |
|---|---|
| `admin@gistar.example` | admin · global |
| `captacion.ia@gistar.example` | captacion · programa P-IA |
| `captacion.data@gistar.example` | captacion · programa P-DATA |
| `seleccion.ia@gistar.example` | seleccion · convocatoria CONV-IA-2027A |
| `docente@gistar.example` | docente · cohortes COH-IA y COH-DATA (sin acceso a admisión) |
| `coordinacion@gistar.example` | coordinacion · global (solo agregados) |
| `aspirante-01@example.test` | persona A-001, sin rol interno |
| `coder-01@example.test` | persona E-001 matriculada en COH-IA, sin rol interno |

## Estructura

```
app/core/      config, db, seguridad (scrypt + token opaco), authz (rol+ámbito), auditoría, deps
app/modules/   identity · catalog · admissions · learning · audit   (un APIRouter por dominio)
alembic/       migraciones revisadas (0001 incluye trigger de solo inserción en audit_event)
tests/         pytest contra PostgreSQL: auth, inscripción, RBAC negativo, CRM, auditoría, contrato
```
