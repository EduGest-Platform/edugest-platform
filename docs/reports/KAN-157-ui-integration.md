# KAN-157 — UI integration / Integración UI

## ES

Implementación: Yohanna. Tarea asignada a Anas; único revisor solicitado: Anasfady. Deadline Jira: **26/11/2026**. Incremento del 24/11/2026.

Añade GET /cohorts autenticado, filtrado por permisos académicos existentes. Docencia y coordinación pueden seleccionar sus cohortes con fechas y zona horaria; sin datos de alumnado, activaciones ni concesión de permisos. Reemplaza la vista local de cohortes en modo API.

## EN

Implementation: Yohanna. Jira assignee: Anas. Sole requested reviewer: Anasfady.

Adds authenticated cohort discovery filtered by existing academic read/aggregate permissions, with a server-backed teacher/coordinator selector, dates and timezone. Exposes no learner roster or activation controls. Backend authorization remains authoritative.

## Validation / Validación

PASS: TypeScript, 81 frontend tests, production build, Ruff, Python compilation and diff checks. OpenAPI exported and TypeScript client regenerated. Five API scope tests added but NOT RUN locally: PostgreSQL unavailable.

## Limits / Límites

CODE_PRESENT_NOT_RUN for DB integration. / Integración DB no ejecutada localmente. Increment for course selection only; activation and roster management are outside this PR. Browser workflow not run.

## CI correction / Corrección CI — 24/11/2026

ES: La primera ejecución de API registró 940 pruebas correctas y un fallo en el caso de aislamiento nuevo. El docente compartido del seed tiene permisos en COH-IA y COH-DATA; el test esperaba solo COH-IA sin limitar sus asignaciones. Ahora ese caso revoca explícitamente los otros ámbitos antes de autenticar. Un sexto caso confirma que el docente conserva ambas cohortes cuando están autorizadas. La API y los permisos no se modifican.

EN: The initial API run recorded 940 passes and one failure in the new isolation test. The shared seed teacher is authorized for both COH-IA and COH-DATA; the test incorrectly expected only one without restricting its assignments. The isolation case now explicitly revokes other scopes before authentication. A sixth API case preserves discovery of both authorized cohorts. API behavior and permissions are unchanged. Full PostgreSQL tests remain not run locally; no claim is made about the corrected CI run.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
