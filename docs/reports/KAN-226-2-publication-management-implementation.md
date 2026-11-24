# KAN-226 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **Sin fecha en Jira / No Jira due date**. Incremento del 24/11/2026.

Añade consulta y listado administrativo paginado de publicaciones, y publicar/retirar con bloqueo de fila, versión esperada y auditoría transaccional. Solo administración global existente, sin conceder roles ni nuevos ámbitos.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Add bounded administrative publication reads and publish/withdraw operations with row locking, optimistic versions and transactional audit. Only existing global administration can manage visibility.

## Validation / Validación

17 offline tests passed; Ruff and TypeScript passed. OpenAPI and TypeScript regenerated. Three PostgreSQL management cases collected only; database runtime unavailable locally.

## Limits / Límites

No UI or general call-content editor. Existing public routes are filtered in phase 4; do not treat this intermediate increment as the complete draft-isolation feature. No CI wait, Jira change, merge or deployment.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
