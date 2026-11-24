# KAN-225 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **Sin fecha en Jira / No Jira due date**. Incremento del 24/11/2026.

Stack 2/5. Administración global puede emitir, renovar y revocar invitaciones para cuentas internas existentes. Solo se persiste hash; renovar revoca los secretos pendientes anteriores. La respuesta de emisión muestra el secreto una sola vez y usa no-store. La ficha permanece pendiente y no hay concesión de roles ni envío externo.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Stack 2/5: global-admin issuance, rotation and revocation for existing internal accounts, hash-only persistence, profile-first invitation locking and atomic metadata-only audit. Issue receipts expose the secret once under API no-store; no role/session mutation or external delivery.

## Validation / Validación

PASS: 13 local policy/contract/anonymous HTTP cases, Ruff, TypeScript and diff checks; OpenAPI/client regenerated. Two PostgreSQL issuance cases added but NOT RUN locally.

## Limits / Límites

Based on the invitation-contract PR #156, independent from the discussion stack. This is not new-user signup or email delivery. Inactive/person accounts cannot be invite targets. / No aceptación funcional ni ejecución PostgreSQL local.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
