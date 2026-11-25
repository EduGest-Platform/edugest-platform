# Learner deliveries / Entregas del alumnado (KAN-56, KAN-234)

ES — El recorrido crea actividades sintéticas publicadas, vencidas, en borrador y de otra cohorte. Comprueba filtros y ámbitos en «Mis entregas». Verifica el rechazo de un enlace HTTP, registra un enlace HTTPS opcional y guarda una segunda revisión que conserva la fecha del primer envío. La API docente revisa la entrega y la pantalla del alumnado deja de ofrecer cambios.

EN — The journey creates synthetic published, overdue, draft and other-cohort assignments. It checks filtering and scope in My Deliveries. It verifies HTTP-link rejection, records an optional HTTPS link and saves a second revision preserving the first submission time. The teacher API marks the submission as reviewed and the learner screen removes editing controls.

## Reproducir / Reproduce

Usa FastAPI y PostgreSQL desechables con la semilla sintética y la web en modo API. Exporta en tu terminal la contraseña sintética usada por el servicio. / Use disposable FastAPI and PostgreSQL with the synthetic seed and the API-mode web app. Export the synthetic password used by the API.

```sh
WEB_URL=http://localhost:8443/ GISTAR_API=http://localhost:8000 CHROME_BIN=chromium node e2e/learner-deliveries.mjs
```
