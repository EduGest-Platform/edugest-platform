# ADR-0008 · Despliegue y CI/CD / Deployment and CI/CD

**Estado / Status:** propuesta (PROPOSED) · **Fecha / Date:** 2026-11-14 · **Responsable / Owner:** Yohanna

## ES

**Decisión.**
- Entorno local: `infra/compose.yaml` levanta PostgreSQL 16, API, web (nginx) y MLflow con un solo comando.
- Despliegue: Render con `render.yaml` (base PostgreSQL 16, API en Docker y web estática). La web se compila con `VITE_GISTAR_API_URL` (ADR-0004).
- CI: GitHub Actions valida web, API, migraciones y que el compose arranca; el E2E se añade cuando exista (YO12).
- Ningún despliegue, cuenta externa ni edición de Jira se ejecuta sin autorización del equipo.

**Motivo.** La rúbrica pide Docker Compose, GitHub Actions y Render. Un solo comando local y un blueprint versionado hacen la demo reproducible.

**Consecuencias.**
- La imagen de la API se construye con la raíz del repositorio como contexto para incluir la semilla sintética.
- El plan gratuito de Render apaga los servicios por inactividad y caduca la base a los 30 días: elegir la fecha de creación con cuidado.
- Solo datos sintéticos; la contraseña demo se genera en Render y no se reutiliza.
- MLflow en compose es para desarrollo y demo (SQLite en un volumen), no para producción.

## EN

**Decision.**
- Local: `infra/compose.yaml` starts PostgreSQL 16, the API, the web app (nginx) and MLflow with one command.
- Deployment: Render via `render.yaml` (PostgreSQL 16, Docker API, static web). The web is built with `VITE_GISTAR_API_URL` (ADR-0004).
- CI: GitHub Actions validates web, API, migrations and that compose starts; E2E is added once it exists (YO12).
- No deployment, external account or Jira edit happens without team authorisation.

**Rationale.** The rubric asks for Docker Compose, GitHub Actions and Render. One local command plus a versioned blueprint makes the demo reproducible.

**Consequences.**
- The API image uses the repository root as build context so it can embed the synthetic seed.
- Render's free plan sleeps idle services and expires the database after 30 days: choose the creation date carefully.
- Synthetic data only; the demo password is generated on Render and never reused.
- MLflow in compose is for development and demo (SQLite on a volume), not production.
