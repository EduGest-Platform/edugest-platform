# KAN-33 — Platform validation / Validación de la plataforma (PF2-PLAT-02)

Status / Estado: VERIFIED locally without Docker, and VERIFIED in GitHub Actions with Docker Compose. NOT_RUN: Docker Compose on the team's machines, deployment on Render. Synthetic data only; no password appears in this document. / Verificado en local sin Docker y en GitHub Actions con Docker Compose. No ejecutado: Compose en las máquinas del equipo, despliegue en Render. Solo datos sintéticos; este documento no contiene contraseñas.

## ES · Resultados

Base: `dev` 8481d08. Local: Linux, Python 3.12, PostgreSQL 16.2 + pgvector 0.6.2 (servidor embebido, **no** la imagen `pgvector/pgvector:pg16`), base de datos vacía y desechable.

| Paso | Resultado |
|---|---|
| Migraciones en base vacía (`alembic upgrade head`) | Versión `0003 (head)`; `alembic check`: «No new upgrade operations detected» |
| Semilla sintética, primera vez y repetida | «datos sintéticos cargados» y después «datos ya presentes, nada que hacer» (es idempotente) |
| `GET /health` con la API arrancada | `{"status":"ok","database":"ok"}` |
| `GET /api/v1/calls` (público) | HTTP 200 |
| Inscripción por el formulario público | Candidatura `IA27A-0007` creada |
| Visible desde otra sesión autorizada (captación IA) | Aparece 1 resultado |
| Tras reiniciar la API (proceso y sesión nuevos, selección IA) | Sigue apareciendo: la candidatura persiste |
| Ámbito: captación Data busca la misma candidatura | 0 resultados |
| Logs de la API (13 líneas) | 0 apariciones del correo de la candidata y 0 de la contraseña; el log de acceso propio muestra ruta, estado, duración e `request_id` |
| Marcha atrás documentada: `downgrade base`, luego `upgrade head` | Sin versión tras bajar; `0003 (head)` al volver a subir |

**Docker Compose (GitHub Actions):** el job `compose` del CI ejecuta `docker compose up -d --build --wait` (db `pgvector/pgvector:pg16`, api, mlflow y web, con sus healthchecks) y `infra/smoke-test.sh` (API `/health` y `/docs`, web, MLflow, login sintético). Está en verde en los PR #37 a #39. El job `registration` (e2e de KAN-140) repite la inscripción pública y la abre desde una sesión de personal en otro contexto de navegador: en verde en #37 y #38.

**Criterios de la historia:** (1) API y PostgreSQL arrancan con datos sintéticos, con health y migración con evidencia: cumplido en local y en el CI. (2) Una candidatura creada permanece y es visible desde otra sesión autorizada: cumplido en local (reinicio de la API) y en el e2e del CI. No se probó «recargar el navegador» en local: lo cubre el e2e en un navegador real.

**Comandos** (en `api/`, con `GISTAR_DATABASE_URL` apuntando a una base de pruebas vacía): `alembic upgrade head`, `python -m app.seed`, `uvicorn app.main:app --no-access-log --port 8765`, `curl /health`, `POST /api/v1/applications`, `GET /api/v1/applications?q=<código>` con la sesión de otra cuenta, reinicio de uvicorn y repetición de la consulta, `alembic downgrade base` y `alembic upgrade head`. La contraseña de las cuentas sintéticas sale de `GISTAR_DEMO_PASSWORD`; no se copia en ningún informe.

## EN · Results

Base: `dev` 8481d08. Local: Linux, Python 3.12, PostgreSQL 16.2 + pgvector 0.6.2 (embedded server, **not** the `pgvector/pgvector:pg16` image), empty disposable database.

| Step | Result |
|---|---|
| Migrations on an empty database (`alembic upgrade head`) | Version `0003 (head)`; `alembic check`: "No new upgrade operations detected" |
| Synthetic seed, first and repeated run | "datos sintéticos cargados", then "datos ya presentes, nada que hacer" (idempotent) |
| `GET /health` with the API running | `{"status":"ok","database":"ok"}` |
| `GET /api/v1/calls` (public) | HTTP 200 |
| Application through the public form | Application `IA27A-0007` created |
| Visible from another authorised session (recruitment IA) | 1 result |
| After restarting the API (new process and session, selection IA) | Still there: the application persists |
| Scope: recruitment Data searches for the same application | 0 results |
| API logs (13 lines) | 0 occurrences of the applicant's email and 0 of the password; the own access log shows path, status, duration and `request_id` |
| Documented rollback: `downgrade base`, then `upgrade head` | No version after downgrading; `0003 (head)` after upgrading again |

**Docker Compose (GitHub Actions):** the CI `compose` job runs `docker compose up -d --build --wait` (db `pgvector/pgvector:pg16`, api, mlflow and web, with their healthchecks) and `infra/smoke-test.sh` (API `/health` and `/docs`, web, MLflow, synthetic login). It is green on PRs #37 to #39. The `registration` job (KAN-140 e2e) repeats the public registration and opens it from a staff session in another browser context: green on #37 and #38.

**Story criteria:** (1) API and PostgreSQL start with synthetic data, with health and migration evidence: met locally and in CI. (2) A created application persists and is visible from another authorised session: met locally (API restart) and in the CI e2e. "Reloading the browser" was not tested locally: the e2e covers it in a real browser.

**Commands** (in `api/`, with `GISTAR_DATABASE_URL` pointing to an empty test database): `alembic upgrade head`, `python -m app.seed`, `uvicorn app.main:app --no-access-log --port 8765`, `curl /health`, `POST /api/v1/applications`, `GET /api/v1/applications?q=<code>` with another account's session, restart uvicorn and repeat the query, `alembic downgrade base` and `alembic upgrade head`. The synthetic accounts' password comes from `GISTAR_DEMO_PASSWORD`; it is not copied into any report.

## Notas tras la revisión / Notes after review

- **ES:** `alembic downgrade base` **borra todas las tablas**: solo se ejecutó en una base vacía y desechable; no usarlo en staging, producción ni en una base con datos que importen. Este informe prueba la cadena `0001 → 0003` sobre `dev` 8481d08. Al integrar KAN-128 (`0004`) y KAN-153 (`0005`), hay que repetir la comprobación de la cadena Alembic y documentarla en un informe aparte, sin reescribir este.
- **EN:** `alembic downgrade base` **drops every table**: it was only run on an empty, disposable database; do not use it on staging, production or any database whose data matters. This report covers the `0001 → 0003` chain on `dev` 8481d08. When KAN-128 (`0004`) and KAN-153 (`0005`) are merged, repeat the Alembic chain check and document it in a separate report, without rewriting this one.
