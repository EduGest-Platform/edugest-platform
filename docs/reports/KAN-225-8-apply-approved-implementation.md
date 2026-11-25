# KAN-225 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **Sin duedate KAN-225; historia KAN-38: 27/11/2026**. Incremento del 25/11/2026.

Aplicación explícita por administración global distinta del solicitante. Bloquea ámbito/usuario/ficha/solicitud, revalida elegibilidad y crea exactamente el rol/ámbito confirmado, vinculándolo a la solicitud y auditoría en la misma transacción. Reintentos no duplican ni reactivan roles.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Apply an approved request through explicit global-admin confirmation. Lock and revalidate target scope/account/profile/request, create the exact role grant and atomically link request/audit. Idempotent retries never recreate revoked assignments; existing active grants are not borrowed.

## Validation / Validación

20 offline policy, confirmation, SQL-lock compilation and anonymous HTTP tests passed; Ruff and TypeScript passed. OpenAPI/client regenerated. Three PostgreSQL application cases collected only.

## Limits / Límites

High-impact role API code, not an executed shared-database grant. PostgreSQL concurrency/transaction behavior NOT RUN locally. No new role permission definitions, account creation, invitation grants, model/migration changes or CI wait. Request-based role revocation remains a follow-up.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
