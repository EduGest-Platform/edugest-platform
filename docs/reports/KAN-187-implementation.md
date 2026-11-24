# KAN-187 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **27/11/2026**. Incremento del 24/11/2026.

Valida que el inicio del periodo de asistencia no sea posterior al fin. Evita métricas vacías que aparentan éxito tanto en sesiones y totales REST como en la herramienta del asistente que reutiliza esos totales. Conserva límites inclusivos, periodos abiertos, autorización previa y supresión de agregados.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Rejects reversed attendance date windows with 422 before session querying, shared by REST metrics and the assistant attendance tool. Preserves inclusive/open bounds, prior scope authorization and existing aggregate suppression. Documents bounds in OpenAPI and regenerates the client.

## Validation / Validación

PASS: six offline date-window/query regressions, TypeScript, Ruff and diff checks; PostgreSQL API cases collected successfully. The inverted-period regression fails before the fix and passes after. Three API cases added but NOT RUN locally.

## Limits / Límites

Increment for attendance indicator filters only, not a complete KPI dashboard. No PostgreSQL/browser validation or deployment. / Incremento de filtros de asistencia; no completa todos los indicadores ni su aceptación.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
