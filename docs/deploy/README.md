# Guía de despliegue / Deployment guide

> Estado / Status: PROPOSED. Nada de esto se ha ejecutado. El despliegue real requiere autorización del equipo.
> Solo datos sintéticos / Synthetic data only.

## ES · Local con Docker Compose

1. `cp infra/.env.example infra/.env` y pon un valor aleatorio largo en `GISTAR_DB_PASSWORD`.
2. `docker compose -f infra/compose.yaml config --quiet` (valida sin imprimir secretos).
3. `docker compose -f infra/compose.yaml up -d --build --wait`
4. `bash infra/smoke-test.sh` y guarda la salida como evidencia (YO1).

| Servicio | URL |
|---|---|
| Web | http://localhost:8443 |
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

## EN · Local with Docker Compose

1. `cp infra/.env.example infra/.env` and set a long random value for `GISTAR_DB_PASSWORD`.
2. `docker compose -f infra/compose.yaml config --quiet` (validates without printing secrets).
3. `docker compose -f infra/compose.yaml up -d --build --wait`
4. `bash infra/smoke-test.sh` and keep the output as evidence (YO1).

Stop and remove volumes with `docker compose -f infra/compose.yaml down -v`.

## EN · Render (only with authorisation)

1. In Render: **New → Blueprint**, pick the repository and confirm `render.yaml`.
2. Render creates `edugest-db`, `edugest-api` and `edugest-web`. Fill the manual values:
   - `edugest-web` → `VITE_GISTAR_API_URL`: the API's public URL (no trailing slash).
   - `edugest-api` → `GISTAR_CORS_ORIGINS`: JSON list with the web's public URL, e.g. `["https://edugest-web.onrender.com"]`.
3. The web is built with the API URL, so redeploy `edugest-web` after setting `VITE_GISTAR_API_URL`.
4. Check `https://<api>/health` and sign in with a synthetic account (password is `GISTAR_DEMO_PASSWORD` in the Render dashboard).

Free-plan limits: services sleep without traffic (slow first request) and the database expires after 30 days.
