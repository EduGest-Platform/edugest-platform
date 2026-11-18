# Guía de despliegue / Deployment guide

> Estado / Status: PROPOSED. Nada de esto se ha ejecutado. El despliegue real requiere autorización del equipo.
> Solo datos sintéticos / Synthetic data only.

Estudio de límites, viabilidad y condiciones pendientes / Limits, feasibility and pending gates: [KAN-142 (17/11/2026)](KAN-142-render-feasibility.md). No autoriza despliegue / Does not authorize deployment.

## ES · Local con Docker Compose

1. `cp infra/.env.example infra/.env` y pon un valor aleatorio largo en `GISTAR_DB_PASSWORD` y otro en `GISTAR_DEMO_PASSWORD` (la contraseña de las cuentas sintéticas; no tiene valor por defecto).
2. `docker compose -f infra/compose.yaml config --quiet` (valida sin imprimir secretos).
3. `docker compose -f infra/compose.yaml up -d --build --wait`
4. `bash infra/smoke-test.sh` y guarda la salida como evidencia (YO1).

| Servicio | URL |
|---|---|
| Web (HTTP, sin TLS; solo local) | http://localhost:8443 |
| API (docs) | http://localhost:8000/docs |
| MLflow | http://localhost:5000 |

Para parar y borrar volúmenes: `docker compose -f infra/compose.yaml down -v`.

## ES · Render (solo con autorización)

1. En Render: **New → Blueprint**, selecciona el repositorio y confirma `render.yaml`.
2. Render crea `edugest-db`, `edugest-api` y `edugest-web`. Rellena los valores marcados como manuales:
   - `edugest-web` → `VITE_GISTAR_API_URL`: URL pública de la API (sin barra final).
   - `edugest-api` → `GISTAR_CORS_ORIGINS`: lista JSON con la URL pública de la web, por ejemplo `["https://edugest-web.onrender.com"]`.
3. Como la web se compila con la URL de la API, vuelve a desplegar `edugest-web` tras fijar `VITE_GISTAR_API_URL`.
4. Comprueba `https://<api>/health` y entra con una cuenta sintética (la contraseña está en `GISTAR_DEMO_PASSWORD`, en el panel de Render).

Límites del plan gratuito: los servicios se duermen sin tráfico (primera petición lenta) y la base caduca a los 30 días.

### Despliegues, migraciones y semilla

- El despliegue automático está desactivado: un `push` no despliega nada. Para desplegar, con autorización del equipo, abre el servicio en Render y usa **Manual Deploy → Deploy latest commit**.
- Las migraciones (`alembic upgrade head`) y la semilla (`python -m app.seed`) corren cada vez que arranca la API, en `api/docker-entrypoint.sh`. No usamos `preDeployCommand`.
- Se pueden repetir sin riesgo: Alembic aplica solo lo pendiente y la semilla no hace nada si ya hay datos (imprime «datos ya presentes»). Para comprobarlo en local: `docker compose -f infra/compose.yaml restart api` y luego `docker compose -f infra/compose.yaml logs --no-color api`.
- MLflow no se despliega en Render; solo existe en el compose local.
- El frontend está en la raíz del repo, por eso `render.yaml` no usa `rootDir`.

## ES · Staging (entorno de pruebas del equipo)

Estado: PROPOSED; no se ha creado en Render. Es un segundo despliegue, con su propia base de datos y sus propios secretos, que sigue la rama `dev`. Sirve para que el equipo vea y pruebe los cambios ya integrados antes de pasarlos a `main`.

| Entorno | Rama | Blueprint | `GISTAR_ENVIRONMENT` | Despliegue |
|---|---|---|---|---|
| local | rama de trabajo | `infra/compose.yaml` | `local` | manual, en tu PC |
| staging | `dev` | `render.staging.yaml` | `staging` | automático si el CI de GitHub pasa (`checksPass`) |
| producción | `main` | `render.yaml` | `production` | manual y autorizado |

Flujo: PR de la rama de trabajo a `dev`, CI y revisión, fusión, staging se despliega solo, el equipo lo prueba, PR de `dev` a `main` y despliegue manual de producción.

Antes de crearlo: la PR de KAN-101 (#37) debe estar integrada en `dev`. Esa PR es la que hace que staging **rechace** la contraseña y la base de datos de demo; sin ella, `GISTAR_ENVIRONMENT=staging` no protege nada y no hay que desplegar.

Crearlo (solo con autorización del PO):

1. En Render: **New → Blueprint**, selecciona el repositorio, rama `dev` y **Blueprint Path** `render.staging.yaml`.
2. Render crea `edugest-db-staging`, `edugest-api-staging` y `edugest-web-staging`. Rellena los valores manuales: `VITE_GISTAR_API_URL` (URL pública de `edugest-api-staging`) y `GISTAR_CORS_ORIGINS` (por ejemplo `["https://edugest-web-staging.onrender.com"]`).
3. Vuelve a desplegar `edugest-web-staging` tras fijar `VITE_GISTAR_API_URL`.
4. Comprueba `/health` y entra con una cuenta sintética. La contraseña es `GISTAR_DEMO_PASSWORD` de staging, en su panel de Render, y es distinta de la de producción.

Comprobaciones tras el primer despliegue (ninguna se ha ejecutado; el CI solo valida el YAML, no que el entorno exista en Render):

- [ ] La API arranca: `/health` devuelve `database: ok`, es decir, conecta con `edugest-db-staging`.
- [ ] Alembic llegó a la última revisión (`alembic current` en el shell de Render) y los datos sintéticos están cargados.
- [ ] El login funciona con la contraseña generada de staging, y la de producción **no** entra.
- [ ] La web de staging llama a la API desde su origen sin error CORS (incluidas las operaciones `PUT`).
- [ ] Staging y producción no comparten base de datos ni secretos: URLs de base distintas y valores de `GISTAR_DEMO_PASSWORD` distintos (comparar sin copiar los valores en ningún texto).

Límites y decisiones pendientes:

- La base gratuita de Render es una por workspace (KAN-142). Decisión del PO (18/11/2026): staging va en el workspace de Elizabeth (PO) y producción en el de Yohanna (SM). Cada workspace tiene su base gratuita y sus 750 horas mensuales, y cada persona conecta su cuenta de Render con el repositorio de GitHub.
- La base gratuita caduca a los 30 días: apuntar la fecha de creación de cada una.
- ADR-0008 dice que ningún push despliega solo. Staging sí lo hace (`checksPass`); producción sigue manual. Requiere aceptación del PO y, después, una nota en ADR-0008.

## EN · Local with Docker Compose

1. `cp infra/.env.example infra/.env` and set a long random value for both `GISTAR_DB_PASSWORD` and `GISTAR_DEMO_PASSWORD` (the password of the synthetic accounts; it has no default).
2. `docker compose -f infra/compose.yaml config --quiet` (validates without printing secrets).
3. `docker compose -f infra/compose.yaml up -d --build --wait`
4. `bash infra/smoke-test.sh` and keep the output as evidence (YO1).

Web is plain HTTP on http://localhost:8443 (no TLS, local only). Stop and remove volumes with `docker compose -f infra/compose.yaml down -v`.

## EN · Render (only with authorisation)

1. In Render: **New → Blueprint**, pick the repository and confirm `render.yaml`.
2. Render creates `edugest-db`, `edugest-api` and `edugest-web`. Fill the manual values:
   - `edugest-web` → `VITE_GISTAR_API_URL`: the API's public URL (no trailing slash).
   - `edugest-api` → `GISTAR_CORS_ORIGINS`: JSON list with the web's public URL, e.g. `["https://edugest-web.onrender.com"]`.
3. The web is built with the API URL, so redeploy `edugest-web` after setting `VITE_GISTAR_API_URL`.
4. Check `https://<api>/health` and sign in with a synthetic account (password is `GISTAR_DEMO_PASSWORD` in the Render dashboard).

Free-plan limits: services sleep without traffic (slow first request) and the database expires after 30 days.

### Deploys, migrations and seed

- Auto-deploy is off: a push deploys nothing. To deploy, with team authorisation, open the service in Render and use **Manual Deploy → Deploy latest commit**.
- Migrations (`alembic upgrade head`) and the seed (`python -m app.seed`) run every time the API starts, in `api/docker-entrypoint.sh`. We do not use `preDeployCommand`.
- They are safe to repeat: Alembic applies only what is pending and the seed does nothing when data already exists (it prints "datos ya presentes"). To check it locally: `docker compose -f infra/compose.yaml restart api`, then `docker compose -f infra/compose.yaml logs --no-color api`.
- MLflow is not deployed to Render; it only exists in the local compose.
- The frontend is at the repo root, which is why `render.yaml` has no `rootDir`.

## EN · Staging (the team's test environment)

Status: PROPOSED; not created on Render. It is a second deployment, with its own database and secrets, that follows the `dev` branch. It lets the team see and test integrated changes before they move to `main`.

| Environment | Branch | Blueprint | `GISTAR_ENVIRONMENT` | Deploy |
|---|---|---|---|---|
| local | working branch | `infra/compose.yaml` | `local` | manual, on your PC |
| staging | `dev` | `render.staging.yaml` | `staging` | automatic when GitHub CI passes (`checksPass`) |
| production | `main` | `render.yaml` | `production` | manual and authorised |

Flow: PR from the working branch to `dev`, CI and review, merge, staging deploys by itself, the team tests it, PR from `dev` to `main`, then a manual production deploy.

Before creating it: the KAN-101 PR (#37) must be merged into `dev`. That PR is what makes staging **reject** the demo password and database; without it `GISTAR_ENVIRONMENT=staging` protects nothing and it must not be deployed.

Create it (only with PO authorisation):

1. In Render: **New → Blueprint**, pick the repository, branch `dev` and **Blueprint Path** `render.staging.yaml`.
2. Render creates `edugest-db-staging`, `edugest-api-staging` and `edugest-web-staging`. Fill the manual values: `VITE_GISTAR_API_URL` (public URL of `edugest-api-staging`) and `GISTAR_CORS_ORIGINS` (for example `["https://edugest-web-staging.onrender.com"]`).
3. Redeploy `edugest-web-staging` after setting `VITE_GISTAR_API_URL`.
4. Check `/health` and sign in with a synthetic account. The password is staging's `GISTAR_DEMO_PASSWORD` in its Render dashboard, and differs from production's.

Checks after the first deploy (none has been run; CI only validates the YAML, not that the environment exists on Render):

- [ ] The API starts: `/health` returns `database: ok`, i.e. it reaches `edugest-db-staging`.
- [ ] Alembic reached the latest revision (`alembic current` in the Render shell) and the synthetic data is loaded.
- [ ] Login works with staging's generated password, and production's password does **not** work.
- [ ] The staging web calls the API from its origin with no CORS error (including `PUT` operations).
- [ ] Staging and production share no database or secrets: different database URLs and different `GISTAR_DEMO_PASSWORD` values (compare without copying the values into any text).

Limits and pending decisions:

- Render's free database is one per workspace (KAN-142). PO decision (18/11/2026): staging lives in Elizabeth's workspace (PO) and production in Yohanna's (SM). Each workspace has its own free database and its own 750 monthly hours, and each person connects their Render account to the GitHub repository.
- The free database expires after 30 days: note the creation date of each one.
- ADR-0008 says no push deploys by itself. Staging does (`checksPass`); production stays manual. This needs PO acceptance and, afterwards, a note in ADR-0008.
