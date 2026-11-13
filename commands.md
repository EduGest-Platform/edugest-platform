# commands.md — Comandos verificados vs previstos / Verified vs planned commands

> Documentación de referencia, no un guion que deba ejecutarse entero. Ningún comando de este archivo se ha ejecutado por crear este documento. **El informe de Codex confirma qué comandos existen y cuáles comprobó el 10/11/2026**. Validar la ruta, el entorno, variables y servicios antes de ejecutar.
>
> English: Reference commands only; check environment and credentials; no production migration without approval.

## Estado / Current evidence (11/11/2026, fase F1)

- `pnpm exec tsc --noEmit -p tsconfig.json`: **PASS**.
- `pnpm test` (Vitest): **PASS** 16/16; el `EPERM` del 10/11 no reaparece (era transitorio).
- `pnpm build`: **PASS** (dist/ generado).
- `docker compose -f infra/compose.yaml up -d --build`: **PASS**; `db` healthy y `api` arrancada con migraciones + seed idempotente.
- API verificada en vivo: `/health` ok+db, login sintético, 401/403 (incl. ámbito horizontal), alta y lectura de candidatura, auditoría y persistencia tras reinicio: **PASS** (detalle en `docs/reports/F1_GIT_DOCKER_POSTGRES_FASTAPI_REPORT.md`).
- **Git:** repositorio propio inicializado el 11/11 en la carpeta del proyecto, rama `main`. Sigue existiendo un repo accidental sin commits en el directorio de usuario de Windows: **no usar Git desde fuera de la carpeta del proyecto** hasta que Eli lo retire. / Own repository initialised 11/11 (branch `main`). An accidental no-commit repo still exists in the Windows user directory: do not run Git from outside the project folder until it is removed.
- **Secretos:** la contraseña local de PostgreSQL vive en `infra/.env` y `api/.env` (ignorados por Git); plantillas en `infra/.env.example` y `api/.env.example`.

## 1. Frontend / Interfaz (PowerShell, raíz del repositorio)

```powershell
node --version
pnpm --version
pnpm install --frozen-lockfile  # approval for dependency install + working repo copy
pnpm exec tsc --noEmit -p tsconfig.json
pnpm test                    # blocked by EPERM in Codex audit: investigate permissions
pnpm build                   # creates dist/ only after baseline verified
pnpm dev                     # local VS Code; NOT if already running inside Figma Make
```

**ES:** Verificar `package.json` y `pnpm-lock.yaml` antes de instalar, no reescribir dependencias para evitar EPERM sin diagnosticarlo. **EN:** Use an isolated writable temp path to diagnose EPERM; do not bypass tests silently.

## 2. PostgreSQL + FastAPI (PowerShell, desde raíz)

```powershell
docker --version
# One-time: copy infra/.env.example to infra/.env and set a random GISTAR_DB_PASSWORD
# (generation snippet inside the example file). Same for api/.env.example -> api/.env.
docker compose -f infra/compose.yaml config --quiet   # validates without printing interpolated secrets
docker compose -f infra/compose.yaml up -d --build
# Check API/DB readiness and ports; commands below assume api dependencies installed
cd api
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"      # check pyproject and consent to install
alembic upgrade head         # LOCAL SYNTHETIC DB ONLY
python -m pytest
uvicorn app.main:app --reload
```

**ES:** Confirmar `api/README.md` y `infra/compose.yaml` (servicios, puertos y nombres) antes de arrancar; no ejecutar Alembic contra BD externa/producción. **EN:** Never copy demo passwords/URL into public docs; use `.env.example` without secrets.

## 3. Contracts & E2E / Contratos y pruebas de recorrido

```powershell
pnpm gen:api         # generates TypeScript from contracts; review diff before commit
pnpm e2e:local      # requires local web services/browser conditions
pnpm e2e:api        # requires FastAPI + PostgreSQL and synthetic users
```

**ES:** Los scripts están identificados en el informe de Codex; sus condiciones reales deben comprobarse en `package.json`. **EN:** The audit listed scripts; it did not execute them.

## 4. Release and operations / Entrega

- `GET /health` (API) and `/docs` (FastAPI/OpenAPI): validate with a running server; do not claim available until checked.
- Before release: local migrations + seed, login and 403 tests, data-source marker, comments isolation, teacher attendance 0.5/1, assistant read-only scope, E2E and backup.
- Deploy only after PO approval, synthetic data, rotated non-default secrets and a rollback/runbook. 04/12 cutoff, rehearsal 09/12, defence 10/12.

## 5. Owner and safety / Propiedad y seguridad

**Eli owns local Git setup and Jira.** This file does not authorise agents to run `git init`, reset branch history, force-push, deploy, open accounts or publish. For any change report exact working tree and tests; never print secrets.
