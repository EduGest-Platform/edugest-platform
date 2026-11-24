# KAN-233 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **Sin fecha en Jira / No Jira due date**. Incremento del 24/11/2026.

Stack 4/5. Añade edición, borrado lógico y resolución/reapertura. Autoría o administración dentro del ámbito pueden modificar; versiones antiguas devuelven 409. El texto borrado se oculta en las respuestas, las respuestas existentes se conservan y cada cambio actualiza versión y auditoría en una transacción.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Stack 4/5: scoped author/admin editing, soft deletion and thread resolution/reopening with observed-version checks. Serializes writes by thread then comment; stale writes return 409, tombstones hide retained content and metadata-only audit remains atomic.

## Validation / Validación

PASS: 22 local contract, anonymous HTTP, tombstone and stale-version cases, Ruff, TypeScript and diff checks. OpenAPI/client regenerated. Three PostgreSQL lifecycle cases added, NOT RUN locally.

## Limits / Límites

Based on #152. No UI, notification or automatic application decision. Body retention is logical deletion, not physical erasure. Resolved threads require explicit reopening before comment changes. / No aceptación funcional ni ejecución PostgreSQL local.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
