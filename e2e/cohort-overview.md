# Server cohort overview / Analítica de cohortes en servidor (KAN-201)

ES — El recorrido abre dos sesiones de Chromium con la API y el PostgreSQL desechables. Comprueba las cifras del seed académico para octubre de 2026, incluidas medias jornadas, estados de entrega y niveles de competencia. Un periodo vacío de asistencia conserva las entregas publicadas y el árbol vigente. Comprueba el cambio a la cohorte Data y que la cuenta de captación recibe 403. Las pruebas de componentes cubren agregados suprimidos y datos ausentes.

EN — The journey opens two Chromium sessions backed by the disposable API and PostgreSQL. It verifies the academic seed's October 2026 figures, including half-days, delivery states and competency levels. An empty attendance period preserves published assignments and the current framework. It tests switching to the Data cohort and verifies that the recruitment account receives 403. Component tests cover suppressed aggregates and missing data.

## Reproducir / Reproduce

Arranca la web en modo servidor y la API con el seed académico. Exporta la contraseña sintética en el entorno. / Start the web in API mode and the API with the academic seed. Export the synthetic password in the environment.

```sh
WEB_URL=http://localhost:8443/ GISTAR_API=http://localhost:8000 CHROME_BIN=chromium node e2e/cohort-overview.mjs
pnpm exec vitest run --configLoader runner src/gistar/__tests__/cohortOverview.test.tsx
```
