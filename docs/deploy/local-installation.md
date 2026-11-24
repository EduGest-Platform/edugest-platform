# Instalación y migraciones locales / Local installation and migrations

## Alcance / Scope

**ES:** Receta para una base PostgreSQL 16 local, desechable y exclusivamente sintética. Estos comandos no autorizan staging, cambios de secretos ni migraciones sobre una base compartida. Las pruebas PostgreSQL no se han ejecutado para esta revisión documental. El [respaldo local](KAN-212-local-fallback.md) y la [prueba de restauración](../../scripts/ci/backup_restore.py) tienen alcances distintos.

**EN:** Recipe for a disposable, synthetic-only local PostgreSQL 16 database. It does not authorize staging, secret rotation or shared database migrations. PostgreSQL tests were not run for this documentation revision. The [local fallback](KAN-212-local-fallback.md) and [restore rehearsal](../../scripts/ci/backup_restore.py) have separate scopes.

## Preparar dependencias / Prepare dependencies

Desde la raíz del repositorio / From the repository root:

```powershell
node --version
pnpm --version
py -3.12 --version
docker compose version
pnpm install --frozen-lockfile
```

Use las versiones del CI y `.mise.toml`; no regenere el lockfile para resolver un entorno local. / Use CI and `.mise.toml` versions; do not regenerate the lockfile to fix a local environment.

Antes de continuar / Before continuing:

| Archivo / File | Acción / Action |
|---|---|
| `infra/.env` | Copiar `infra/.env.example` solo si no existe; configurar valores aleatorios locales para DB y cuentas sintéticas. / Copy the template only if absent and configure random local values. |
| `api/.env` | Copiar `api/.env.example` solo si no existe; ajustar la misma contraseña de DB en las dos URLs y definir la contraseña de cuentas antes del seed. / Match the DB password in both URLs and set the account password before seeding. |
| Entorno / Environment | `GISTAR_ENVIRONMENT=local`, únicamente en localhost. / Localhost only. |

No imprimir, copiar a tickets ni versionar los valores. Cambiar `.env` no cambia contraseñas de cuentas ya creadas. / Never print, paste into tickets or commit values. Editing `.env` does not rotate existing account passwords.

## Base de datos / Database

Desde la raíz / From the root:

```powershell
docker compose --env-file infra/.env -f infra/compose.yaml up -d db
```

La inicialización del volumen crea `gistar` y `gistar_test`; no se repite en un volumen existente. Si falta la base de pruebas, revisar `infra/initdb/01-test-db.sql` con la persona responsable; no borrar el volumen para arreglarlo. / Initial volume setup creates both databases and does not repeat for an existing volume. Review the init SQL with the owner if the test DB is missing; do not delete the volume as a repair.

## API y esquema / API and schema

PowerShell, desde la raíz / from the root:

```powershell
cd api
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m alembic heads
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic check
.\.venv\Scripts\python.exe -m app.seed
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --reload --no-access-log
```

**ES:** Confirmar la URL de destino sin divulgarla antes de `upgrade`. Una sola cabeza y `alembic check` sin deriva son requisitos; editar modelos no actualiza una base existente. `app.seed` es idempotente y no rota cuentas ya cargadas. No usar `--reset`, `downgrade base` ni `down -v` en una base compartida. La API registra rutas parametrizadas; `--no-access-log` evita que uvicorn duplique rutas/query strings sin sanear.

**EN:** Confirm the target without exposing its URL before upgrading. Require one head and no model drift; model edits alone do not migrate an existing DB. Seed is idempotent and does not rotate existing accounts. Never use reset, downgrade-to-base or volume deletion against shared data. Disable uvicorn access logging because the application already logs sanitized route templates.

POSIX: dentro de `api`, usar `python3.12 -m venv .venv` y sustituir `.\.venv\Scripts\python.exe` por `.venv/bin/python` en los mismos pasos. / On POSIX, use the same steps with the POSIX virtualenv executable. No activation is required.

## Web y contrato / Web and contract

En otra terminal, raíz del repo / Separate terminal at repository root:

```powershell
$env:VITE_GISTAR_API_URL='http://localhost:8000'
pnpm dev --host 127.0.0.1
```

POSIX: `VITE_GISTAR_API_URL=http://localhost:8000 pnpm dev --host 127.0.0.1`.

ES: CORS debe incluir el origen exacto mostrado por Vite. Sin esta variable la web usa datos locales; no prueba persistencia ni RBAC. Las vistas migradas están enumeradas en `src/shared/api/config.ts`; las demás muestran su aviso local.

EN: CORS must include Vite's exact displayed origin. Without the API URL, browser-local data does not prove persistence or RBAC. `API_VIEWS` is the current registry of migrated screens; remaining screens retain their local warning.

Para un cambio de contrato / For contract changes:

```powershell
# Dentro de api / Inside api:
.\.venv\Scripts\python.exe scripts/export_openapi.py
# Volver a raíz / Return to root:
cd ..
pnpm gen:api
git diff -- contracts/openapi.json src/shared/api/schema.gen.ts
```

Revisar ambos archivos; no editar el cliente generado manualmente. / Review both files; do not hand-edit generated client types.

## Pruebas y evidencia / Tests and evidence

**ES:** `api/tests/conftest.py` exige `GISTAR_TEST_DATABASE_URL` en el entorno del proceso. La carga normal de `api/.env` por Settings no exporta esa variable para el conftest. Configurarla mediante un mecanismo local que no la imprima y verificar que termina en la base **de pruebas**: pytest ejecuta downgrade/upgrade y vacía tablas. Nunca apuntar a la base usada por otra persona o por la demo.

**EN:** The test conftest requires `GISTAR_TEST_DATABASE_URL` in the process environment. Settings loading `.env` does not export it for conftest. Set it through a local mechanism that does not print the value, verify the isolated test DB target, and remember pytest migrates and truncates it. Never target shared/demo data.

```powershell
# Dentro de api, solo con la variable de base de pruebas ya preparada:
# Inside api, only after the isolated test database variable is set:
.\.venv\Scripts\python.exe -m pytest
```

Desde raíz / From root: `pnpm exec tsc --noEmit -p .`, `pnpm test`, `pnpm build`. Registrar comando, fecha y resultado real; un comando documentado no es evidencia de ejecución. / Record actual command, date and result; documentation is not execution evidence.

## Diagnóstico / Troubleshooting

| Síntoma / Symptom | Revisión / Check |
|---|---|
| Arranque rechaza secretos / Startup rejects secrets | Revisar entorno y configuración, sin imprimir valores; no desactivar el validador. / Check environment/config without printing values; do not disable validation. |
| Error de directorio Alembic / Alembic directory error | Ejecutar desde `api`; `script_location` es relativo. / Run inside `api`; migration paths are relative. |
| Contrato desactualizado / Stale contract | Exportar OpenAPI, regenerar TS y revisar diff. / Export OpenAPI, regenerate TS and inspect both diffs. |
| Falta tabla / Missing table | Revisar cabeza/corriente y migraciones de la rama; no llamar a `create_all` como sustituto. / Check branch migrations; do not replace migrations with `create_all`. |
| Seed no cambia cuentas / Seed does not change accounts | Es idempotente; coordinar recuperación del entorno sintético local. / It is idempotent; coordinate local synthetic recovery. |
