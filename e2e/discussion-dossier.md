# Internal dossier discussions / Comentarios internos del expediente (KAN-74, KAN-235, KAN-245)

ES — El recorrido crea un expediente sintético y abre dos sesiones de captación. Comprueba el foco del teclado, la creación de un hilo, la respuesta, el texto literal y los cambios de estado. Una sesión envía una edición antigua. La otra versión se mantiene y la interfaz conserva el borrador hasta que la persona carga y acepta la versión actual. La API deniega la consulta a captación de otro programa.

EN — The journey creates a synthetic dossier and opens two recruitment sessions. It verifies keyboard focus, thread creation, replies, literal comment text and resolution changes. One session sends a stale edit. The newer version stays in place and the UI preserves the draft until the user loads and accepts the current version. The API denies discussion reads by recruitment staff from a different programme.

## Reproducir / Reproduce

Arranca la web en modo API y el servicio con PostgreSQL y la semilla sintética. Exporta la contraseña sintética compartida con la API. / Start the API-mode web app and the API with PostgreSQL and the synthetic seed. Export the synthetic demo password used by the API.

```sh
WEB_URL=http://localhost:8443/ GISTAR_API=http://localhost:8000 CHROME_BIN=chromium node e2e/discussion-dossier.mjs
```
