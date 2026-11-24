# KAN-233 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **Sin fecha en Jira / No Jira due date**. Incremento del 24/11/2026.

Stack 2/5, depende de #150. Expone creación, consulta individual y listado paginado de hilos por un ámbito exacto. Autor y fechas son del servidor; el alta y su auditoría comparten transacción. No cambia etapas de candidatura ni permite ampliar acceso de convocatoria a programa.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Stack 2/5, based on #150: scoped thread creation, individual reads and paginated single-scope listing. Server-controlled authorship and atomic metadata-only audit; no application-state changes or new permission grants.

## Validation / Validación

PASS: 13 local contract/anonymous HTTP cases, Ruff, TypeScript and diff checks. OpenAPI/client regenerated. Three PostgreSQL integration cases added, NOT RUN locally.

## Limits / Límites

Discussion contents are internal to existing applications.read/crm scopes. Program threads are intentionally unavailable to call-only assignments. No comment routes until the next stack layer. PostgreSQL execution remains pending. / No cierre de Jira ni aceptación PO.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
