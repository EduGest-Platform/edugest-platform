# KAN-85 — Health, connectivity, rollback and logs / Health, conectividad, marcha atrás y logs

Base: `dev` at `6a55b66` (Alembic head `0005`; chain `0001 → 0003 → 0004 → 0006 → 0007 → 0005`). Machine: Windows 10 Pro, Python venv (uv), PostgreSQL 16 + pgvector in the local `infra-db-1` container. All runs used **new disposable databases** (`kan85_scratch` for the runtime checks, a separate test database for pytest). The shared `gistar` and `gistar_test` databases were not touched. Synthetic data only; no password, URL credential or personal data appears in this report. Follows [KAN-33](KAN-33-platform-validation.md), which covered the `0001 → 0003` chain.

## EN

### Code change: `/health` reports a lost database as 503, fast

Before, if PostgreSQL was unreachable, `/health` answered a generic **500**. It also took **130 s** on Windows, because the engine had no connect timeout and waited for the OS TCP timeout. Docker's healthcheck gives up after 3 s, and monitors could not tell "API broken" from "database down".

- `api/app/main.py`: `/health` catches `SQLAlchemyError`, answers **503** `{"status":"degraded","database":"unavailable"}` and logs `health check: database unavailable`, with no host, user or driver message. The 503 response is documented in OpenAPI. `contracts/openapi.json` and `src/shared/api/schema.gen.ts` are regenerated (LF).
- `api/app/core/db.py`: `connect_timeout=5` s on the engine (`DATABASE_CONNECT_TIMEOUT_SECONDS`). This does not change behaviour when the database is reachable.
- `api/tests/test_health.py`: 200 with the database, and 503 with a failing session. The test asserts that host, user and driver text never reach the response or the logs.

### Evidence

| Check | Result |
|---|---|
| `GET /health`, database up | `{"status":"ok","database":"ok"}` HTTP 200 |
| `GET /api/v1/calls` | HTTP 200 |
| `POST /api/v1/applications` (synthetic applicant) | HTTP 201, code `IA27A-0007` |
| `GET /health`, database unreachable (closed port), **before** the timeout | HTTP 503 after **130.3 s** |
| `GET /health`, database unreachable, **after** (`connect_timeout=5`) | HTTP 503 `{"status":"degraded","database":"unavailable"}` in **5.4 s** |
| Logs, both servers | Access line with route template, status, duration and `request_id`; 0 occurrences of the applicant's email; 0 of the DB user or password; the 503 log has no driver details |
| `alembic upgrade head` on empty DB, then `alembic check` | `0005 (head)`; "No new upgrade operations detected" |
| Seed twice | "datos sintéticos cargados", then "datos ya presentes" (idempotent) |
| Step-by-step rollback `downgrade -1` ×5 | `0005`(19 tables) → `0007`(18) → `0006`(17) → `0004`(16) → `0003`(14) → `0001`(12), all exit 0 |
| `upgrade head` again, `alembic check` | `0005 (head)`, 19 tables, no pending operations |
| `downgrade base`, then `upgrade head` + seed | No revision after base; `0005 (head)` and seed loaded again |
| `pytest` complete API suite (disposable test DB) | See PR body (run on this branch) |
| `ruff check . --select E4,E7,E9,F` (0.17.5) | PASS |

### Rollback guidance

- **Code:** revert the merge commit of the PR. The change touches no migration or data.
- **Schema:** `alembic downgrade -1` steps back one revision (order above). `alembic downgrade base` **drops every table**: use it only on empty, disposable databases, never on staging, production or any database whose data matters. A production schema rollback needs a backup and PO approval first.

NOT_RUN: Docker Compose on this machine (the running `infra-*` stack belongs to other work and was not restarted; the CI `compose` job covers it), Render, browser E2E.

## ES

**Cambio de código.** Si PostgreSQL no responde, `/health` devuelve **503** `{"status":"degraded","database":"unavailable"}` en lugar de un 500 genérico. El log no incluye host, usuario ni mensaje del driver. El motor tiene `connect_timeout=5`: antes la respuesta tardaba 130 s en Windows, ahora 5,4 s. Contrato OpenAPI y cliente TS regenerados. Nueva prueba `test_health.py`.

**Evidencia.**
- Health OK con base de datos; `/calls` 200; alta de candidatura sintética 201.
- Logs sin correo ni credenciales.
- Cadena Alembic completa hacia atrás paso a paso (`0005 → 0007 → 0006 → 0004 → 0003 → 0001`) y vuelta a `head` sin operaciones pendientes. `downgrade base` y `upgrade head` correctos.
- Todo en bases desechables. `gistar` y `gistar_test` no se tocaron.

**Marcha atrás.** Código: revertir el commit de merge. Esquema: `downgrade -1`. `downgrade base` borra todas las tablas: nunca en staging ni producción. Una vuelta atrás en producción exige copia de seguridad y aprobación de la PO.

**No ejecutado:** Compose en esta máquina (lo cubre el job `compose` del CI), Render, E2E de navegador.
