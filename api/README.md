# EduGest API

FastAPI + SQLAlchemy 2 + Alembic sobre **PostgreSQL** (nunca SQLite: las pruebas usan la misma base que producción).
Datos **exclusivamente sintéticos**. La autorización se comprueba en el servidor por **rol + ámbito**.

## Arranque local

```bash
cd api
python -m venv .venv && . .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env              # pon la contraseña de infra/.env en GISTAR_DATABASE_URL (ver infra/.env.example)
# En .env, configura GISTAR_DEMO_PASSWORD con un valor seguro, no vacío y distinto por entorno antes de continuar.
# In .env, set GISTAR_DEMO_PASSWORD to a strong, non-empty, environment-specific value before continuing.
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

## Configuración de despliegue / Deployment configuration

**ES:** Sin `GISTAR_ENVIRONMENT`, la API asume `production` y falla si faltan secretos. `GISTAR_ENVIRONMENT=local` es solo para desarrollo en localhost. Antes de exponer la API, configura `staging` o `production`, una `GISTAR_DEMO_PASSWORD` única de al menos 20 caracteres y `GISTAR_DATABASE_URL` para la base de ese entorno. La API rechaza el arranque si se conserva la contraseña demo o la URL de base de datos por defecto. Guarda los valores reales en los secretos del proveedor, nunca en Git.

**EN:** Without `GISTAR_ENVIRONMENT`, the API assumes `production` and fails when secrets are missing. `GISTAR_ENVIRONMENT=local` is for localhost development only. Before exposing the API, set `staging` or `production`, a unique `GISTAR_DEMO_PASSWORD` of at least 20 characters, and the environment's `GISTAR_DATABASE_URL`. The API refuses to start with the default demo password or database URL. Keep real values in the provider's secret store, never in Git.

## Cuentas sintéticas (contraseña: `GISTAR_DEMO_PASSWORD` configurada en `.env`)

La plantilla deja `GISTAR_DEMO_PASSWORD` vacía: debes definirla **antes del seed y del arranque**. Una variable vacía no usa el valor por defecto del código; generaría cuentas con contraseña vacía que el login no acepta. No publiques la contraseña ni el archivo `.env`. Si ya cargaste el seed con un valor vacío, cambiar `.env` no actualiza las cuentas existentes: coordina la corrección del seed local sintético antes de continuar.

**EN:** The template leaves `GISTAR_DEMO_PASSWORD` empty. Set it **before seeding and startup**; an empty variable overrides the code fallback and creates accounts whose empty password the login rejects. Never publish the password or `.env`. Changing `.env` does not update already seeded accounts; coordinate correction of the local synthetic seed if it was loaded with an empty value.

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

## Migraciones: orden real de la cadena / Alembic chain order

**ES.** Los números de fichero no siguen el orden de ejecución. No existe la `0002`, y la `0005` se re-colgó de la `0007` al integrar ramas. El orden real es:

`0001 → 0003 → 0004 → 0006 → 0007 → 0005 → 0008 → 0009 → 0010 → 0011`

No se renumera: cambiar `revision` en una base ya migrada (staging) rompería `alembic upgrade`. Una migración nueva siempre cuelga del *head* actual (`alembic heads`), sin fijarse en el número más alto. El CI aplica `downgrade base` + `upgrade head` en cada ejecución de tests.

**EN.** File numbers do not follow execution order. There is no `0002`, and `0005` was re-parented onto `0007` when branches were merged. The real order is the chain above. We do not renumber, because changing `revision` on an already migrated database (staging) would break `alembic upgrade`. A new migration always hangs from the current head (`alembic heads`), whatever the highest number is. CI runs `downgrade base` + `upgrade head` on every test run.

## Límite de intentos de inicio de sesión / Login attempt limit

**ES.** Tras `GISTAR_LOGIN_MAX_FAILURES` (5) fallos para la misma cuenta en `GISTAR_LOGIN_WINDOW_MINUTES` (15) minutos, `/auth/login` responde `429` con `Retry-After`, aunque la contraseña sea correcta. Por cliente el límite es 4 veces mayor. Un acceso correcto reinicia el contador de la cuenta. Los contadores viven en memoria, con claves SHA-256 sin correo ni IP en claro: vale para una sola instancia. Con varias instancias hay que moverlos a base de datos o a una caché compartida. Detrás de un proxy (Render), `GISTAR_TRUSTED_PROXY_HOPS=1` (en `render*.yaml`) hace que la IP por cliente sea la entrada **más a la derecha** de `X-Forwarded-For`, la que añade el proxy. Las de la izquierda las escribe el cliente y nunca se usan. Con 0 (local) se ignora la cabecera. **Pendiente de verificar en staging**, y de nuevo si cambia la cadena de proxies: enviar `X-Forwarded-For: 1.2.3.4` y confirmar que la entrada de más a la derecha es tu IP pública. Si Render añade más saltos, sube el valor.

**EN.** After `GISTAR_LOGIN_MAX_FAILURES` (5) failures for the same account within `GISTAR_LOGIN_WINDOW_MINUTES` (15) minutes, `/auth/login` answers `429` with `Retry-After`, even when the password is correct. The per-client limit is 4 times higher. A successful login clears the account counter. Counters are kept in memory under SHA-256 keys, with no e-mail or IP in clear text, so this only covers a single instance. With several instances they must move to the database or a shared cache. Behind a proxy (Render), `GISTAR_TRUSTED_PROXY_HOPS=1` (in `render*.yaml`) makes the per-client IP the **right-most** `X-Forwarded-For` entry, the one the proxy appends. Entries to its left are client-written and never used. With 0 (local), the header is ignored. **To verify on staging**, and again whenever the proxy chain changes: send `X-Forwarded-For: 1.2.3.4` and confirm the right-most entry is your public IP. If Render adds more hops, raise the value.

## Estructura

```
app/core/      config, db, seguridad (scrypt + token opaco), authz (rol+ámbito), auditoría, deps
app/modules/   identity · catalog · admissions · learning · audit   (un APIRouter por dominio)
alembic/       migraciones revisadas (0001 incluye trigger de solo inserción en audit_event)
tests/         pytest contra PostgreSQL: auth, inscripción, RBAC negativo, CRM, auditoría, contrato
```
