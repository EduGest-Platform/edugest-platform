# Own learner progress / Progreso del alumnado (KAN-49, KAN-177)

ES — Abre dos contextos de Chromium sobre la misma API y el mismo PostgreSQL sintético. La cuenta de coder ve su matrícula, sus totales de asistencia, sus niveles actuales de competencias y sus entregas publicadas. La matrícula se conserva al recargar. La cuenta de aspirante conserva su navegación y recibe 404 en las dos rutas de progreso propio si usa el identificador de la matrícula de coder. El recorrido verifica que ambas sesiones permanecen independientes.

EN — Opens two Chromium contexts backed by the same API and synthetic PostgreSQL. The coder sees their enrollment, attendance totals, current competency levels and published assignments. The enrollment still appears after reload. The applicant keeps their own navigation and receives 404 from both own-progress routes for the coder's enrollment ID. The journey verifies that both sessions remain independent.

## Reproducir / Reproduce

Arranca la API con las migraciones y la semilla sintética académica y sirve la web en modo API. Exporta la contraseña sintética en el entorno. / Start the API with migrations and the synthetic academic seed, and serve the API-mode web app. Export the synthetic demo password in the environment.

```sh
WEB_URL=http://localhost:8443/ GISTAR_API=http://localhost:8000 CHROME_BIN=chromium node e2e/learner-progress.mjs
```

La prueba utiliza cuentas sintéticas existentes y rutas de lectura. GitHub Actions la ejecuta con el Compose desechable. / The test uses existing synthetic accounts and read endpoints. GitHub Actions runs it against the disposable Compose environment.
