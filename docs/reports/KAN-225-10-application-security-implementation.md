# KAN-225 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **Sin duedate KAN-225; historia KAN-38: 27/11/2026**. Incremento del 25/11/2026.

Añade matriz de autorización antes de consultar recursos, conflictos entre solicitudes, rollback de asignación y auditoría y regresión PostgreSQL del bloqueo FK concurrente. Documenta el contrato y los límites del stack.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Add authorization-before-lookup matrix, conflicting-request and audit rollback regressions, plus a PostgreSQL concurrent FK lock regression. Document the application contract and remaining scope.

## Validation / Validación

59 offline Python tests passed; 117 web tests passed; Ruff, TypeScript and schema reference checks passed. Nine PostgreSQL API cases collected only.

## Limits / Límites

No local PostgreSQL runtime; database and concurrent transaction tests not executed locally. KAN-225 remains partial: request-based revocation, provisioning, mail and UI are outside this stack.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
