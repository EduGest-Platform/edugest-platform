# KAN-233 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **Sin fecha en Jira / No Jira due date**. Incremento del 24/11/2026.

Stack 3/5. Añade comentarios y respuestas paginados, con autor del servidor y validación de padre dentro del mismo hilo. El bloqueo del hilo serializa escrituras y el incremento de versión comparte transacción con auditoría; los hilos resueltos rechazan nuevas respuestas.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Stack 3/5: scoped comment/reply creation and listing, immutable parent references, server authorship and same-thread parent validation. Thread locking, revision bump and metadata-only audit are atomic; resolved threads reject writes.

## Validation / Validación

PASS: 15 local contract/anonymous HTTP cases, Ruff, TypeScript and diff checks. OpenAPI/client regenerated. Four PostgreSQL integration cases added, NOT RUN locally.

## Limits / Límites

Based on #151. No UI or external notifications. Comment text is JSON/plain text; any future UI must escape it. Does not grant academic/person accounts internal CRM access. / Sin ampliar permisos ni cerrar Jira.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
