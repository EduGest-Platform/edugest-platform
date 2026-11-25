# commands.md — Comandos verificados vs previstos / Verified vs planned commands

> Documentación de referencia, no un guion que deba ejecutarse entero. Ningún comando de este archivo se ha ejecutado por crear este documento. **El informe de Codex confirma qué comandos existen y cuáles comprobó el 10/11/2026**. Validar la ruta, el entorno, variables y servicios antes de ejecutar.
>
> English: Reference commands only; check environment and credentials; no production migration without approval.

## Estado / Current evidence (19/11/2026, KAN-86)

Verified on Windows 10 Pro (Git Bash and PowerShell), Node 24.18.0, pnpm 10.34.3, Python venv created with `uv`, PostgreSQL 16 + pgvector in the local Docker container. Base `dev` `6a55b66`. Synthetic data only. No password or connection string is written here: they live in the git-ignored `infra/.env` and `api/.env` (templates: `*.env.example`).

| Command | Result 19/11 |
|---|---|
| `pnpm install --frozen-lockfile` | PASS, 12.7 s |
| `pnpm exec tsc --noEmit -p .` | PASS |
| `pnpm test` (Vitest) | PASS, 5 files / 48 tests, 3.0 s (see KAN-87 for the Windows `EPERM` cause and fix) |
| `pnpm build` | PASS (`dist/`, 443 kB JS) |
| `uv venv .venv` + `uv pip install -e ".[dev]"` (in `api/`) | PASS |
| `alembic upgrade head` / `alembic check` on an empty DB | `0005 (head)`; no pending operations |
| `python -m app.seed` (twice) | Loaded, then "datos ya presentes" (idempotent) |
| `uvicorn app.main:app --port 8785 --no-access-log` + `curl /health` | `{"status":"ok","database":"ok"}` |
| `pytest` (complete API suite, disposable test DB) | PASS: 559 tests, 0 failures, 0 errors (KAN-85 branch, which adds 2 health tests to `dev`) |
| `ruff check . --select E4,E7,E9,F` (0.17.5, in `api/`) | PASS |
| `docker compose -f infra/compose.yaml up -d --build --wait` + `infra/smoke-test.sh` | NOT_RUN locally on 19/11 (shared stack already running); PASS in the CI `compose` job on every PR |

Older evidence: F1 on 11/11 (`docs/reports/F1_GIT_DOCKER_POSTGRES_FASTAPI_REPORT.md`) and KAN-33 (`docs/reports/KAN-33-platform-validation.md`).

## 1. Frontend / Interfaz (repository root)

The project uses **pnpm** (`pnpm-lock.yaml`); `npm ci` fails because there is no `package-lock.json`.

```bash
node --version
pnpm --version
pnpm install --frozen-lockfile
pnpm exec tsc --noEmit -p .
pnpm test                    # Vitest, once; `pnpm exec vitest` for watch mode
pnpm build                   # creates dist/
pnpm dev                     # local only; NOT if Figma Make already runs the preview
VITE_GISTAR_API_URL=http://localhost:8000 pnpm dev   # web against the local API (API mode)
```

**ES:** si Vitest falla con `EPERM` en `node_modules/.vite-temp`, ver `docs/reports/KAN-87-vitest-eperm.md`; no saltarse las pruebas. **EN:** if Vitest fails with `EPERM` on `node_modules/.vite-temp`, see the KAN-87 report; never skip the tests.

## 2. PostgreSQL + FastAPI

```bash
# One-time: copy infra/.env.example to infra/.env and api/.env.example to api/.env,
# set a random GISTAR_DB_PASSWORD and GISTAR_DEMO_PASSWORD (no defaults; never commit them).
docker compose -f infra/compose.yaml config --quiet   # validates without printing secrets
docker compose -f infra/compose.yaml up -d --build --wait
cd api
uv venv .venv                     # or: python -m venv .venv
uv pip install -p .venv -e ".[dev]"
.venv/Scripts/python -m alembic upgrade head   # Windows; .venv/bin/python on Linux/macOS. LOCAL SYNTHETIC DB ONLY
.venv/Scripts/python -m app.seed
.venv/Scripts/python -m uvicorn app.main:app --reload --no-access-log   # http://localhost:8000/docs and /health
```

**Tests (API).** `pytest` migrates `base → head` and empties its database on every run. Point `GISTAR_TEST_DATABASE_URL` at a database **only you** use: two runs on the same test database break each other.

```bash
set -a; . ./.env; set +a          # bash: load api/.env without printing it
export GISTAR_ENVIRONMENT=local
.venv/Scripts/python -m pytest -p no:cacheprovider --basetemp="$PWD/.pytest-tmp"   # pyproject already adds -q; another -q hides the summary
```

- Windows with Git Bash: `--basetemp="$PWD/.pytest-tmp"` keeps pytest temporary files under the current `api/` working directory instead of the system temp folder. The complete suite takes more than 10 minutes.
- After changing the API contract: `python -m scripts.export_openapi`, convert `contracts/openapi.json` to LF, then `pnpm gen:api`.

**ES:** no ejecutar Alembic contra una base externa ni de producción; `alembic downgrade base` borra todas las tablas. **EN:** never run Alembic against an external or production database; `downgrade base` drops every table.

## 3. Contracts & E2E / Contratos y pruebas de recorrido

### Model-only ERD/dictionary / ERD y diccionario de modelos (KAN-216)

From repository root, with `GISTAR_ENVIRONMENT=local`: / Desde la raíz, con ese entorno:

```bash
python api/scripts/export_schema_reference.py          # regenerate; review the diff / regenerar y revisar
python api/scripts/export_schema_reference.py --check  # read-only freshness check / comprobar sin reescribir
```

No database connection, migration or deployed-schema inspection. A failed check does not overwrite the reference. CI runs it from `api`; keep `alembic check` separate. / No conecta a una BD ni ejecuta migraciones. El fallo no reescribe la referencia; la comprobación de migraciones sigue siendo independiente.

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
