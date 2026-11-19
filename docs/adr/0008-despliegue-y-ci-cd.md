# ADR-0008 · Despliegue y CI/CD / Deployment and CI/CD

**Estado / Status:** propuesta (PROPOSED) · **Fecha / Date:** 2026-11-14 · **Responsable / Owner:** Yohanna

## ES

**Decisión.**
- Entorno local: `infra/compose.yaml` levanta PostgreSQL 16, API, web (nginx) y MLflow con un solo comando.
- Despliegue: Render con `render.yaml` (base PostgreSQL 16, API en Docker y web estática). La web se compila con `VITE_GISTAR_API_URL` (ADR-0004).
- CI: GitHub Actions valida web, API, migraciones y que el compose arranca; el E2E se añade cuando exista (YO12).
- Ningún despliegue, cuenta externa ni edición de Jira se ejecuta sin autorización del equipo. Por eso el despliegue automático está desactivado (`autoDeployTrigger: "off"`) en la API y la web: nada se despliega con un `push`.
- Migraciones y semilla: se ejecutan al arrancar la API, en `api/docker-entrypoint.sh` (`alembic upgrade head` y `python -m app.seed`), no con `preDeployCommand`. Ambas se pueden repetir sin riesgo: Alembic aplica solo lo pendiente y la semilla no hace nada si ya hay datos.
- El frontend está en la raíz del repositorio (ADR-0001), así que la web no necesita `rootDir`.
- API y base de datos van en la región `frankfurt` (la red interna exige la misma región) y la base no admite conexiones desde internet (`ipAllowList: []`).
- MLflow no se despliega en Render: solo existe en el compose local.
- **Excepción para staging (decisión de la PO, 19/11/2026):** `render.staging.yaml` despliega automáticamente cada push a `dev` cuando pasan los checks de GitHub (`autoDeployTrigger: checksPass`). Staging tiene base de datos y secretos propios y solo datos sintéticos. Producción (`render.yaml`) sigue con `autoDeployTrigger: "off"`. Crear los recursos en Render sigue necesitando autorización.

**Motivo.** La rúbrica pide Docker Compose, GitHub Actions y Render. Un solo comando local y un blueprint versionado hacen la demo reproducible.

**Consecuencias.**
- La imagen de la API se construye con la raíz del repositorio como contexto para incluir la semilla sintética.
- El plan gratuito de Render apaga los servicios por inactividad y caduca la base a los 30 días: elegir la fecha de creación con cuidado.
- Solo datos sintéticos; la contraseña demo se genera en Render y no se reutiliza.
- MLflow en compose es para desarrollo y demo (SQLite en un volumen), no para producción.
- Cada reinicio de la API vuelve a ejecutar el entrypoint; si una migración o la semilla falla, el servicio no arranca y el fallo se ve en los registros.

## EN

**Decision.**
- Local: `infra/compose.yaml` starts PostgreSQL 16, the API, the web app (nginx) and MLflow with one command.
- Deployment: Render via `render.yaml` (PostgreSQL 16, Docker API, static web). The web is built with `VITE_GISTAR_API_URL` (ADR-0004).
- CI: GitHub Actions validates web, API, migrations and that compose starts; E2E is added once it exists (YO12).
- No deployment, external account or Jira edit happens without team authorisation. That is why auto-deploy is off (`autoDeployTrigger: "off"`) on the API and the web: no push deploys anything.
- Migrations and seed run when the API starts, in `api/docker-entrypoint.sh` (`alembic upgrade head` and `python -m app.seed`), not via `preDeployCommand`. Both are safe to repeat: Alembic applies only what is pending and the seed does nothing when data already exists.
- The frontend lives at the repository root (ADR-0001), so the web needs no `rootDir`.
- API and database use the `frankfurt` region (the private network requires the same region) and the database accepts no connections from the internet (`ipAllowList: []`).
- MLflow is not deployed to Render: it only exists in the local compose.
- **Staging exception (PO decision, 19/11/2026):** `render.staging.yaml` deploys every push to `dev` automatically once GitHub checks pass (`autoDeployTrigger: checksPass`). Staging has its own database and secrets and synthetic data only. Production (`render.yaml`) keeps `autoDeployTrigger: "off"`. Creating the resources on Render still requires authorisation.

**Rationale.** The rubric asks for Docker Compose, GitHub Actions and Render. One local command plus a versioned blueprint makes the demo reproducible.

**Consequences.**
- The API image uses the repository root as build context so it can embed the synthetic seed.
- Render's free plan sleeps idle services and expires the database after 30 days: choose the creation date carefully.
- Synthetic data only; the demo password is generated on Render and never reused.
- MLflow in compose is for development and demo (SQLite on a volume), not production.
- Every API restart runs the entrypoint again; if a migration or the seed fails, the service does not start and the failure shows in the logs.
