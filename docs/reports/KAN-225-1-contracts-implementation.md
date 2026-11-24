# KAN-225 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **Sin fecha en Jira / No Jira due date**. Incremento del 24/11/2026.

Stack independiente 1/5: contratos estrictos, secreto de aceptación redactado en repr, elegibilidad de cuentas internas activas y límites de caducidad. Solo autoridad administrativa global puede gestionar invitaciones; no se habilita permiso de Fundación mientras KAN-222 esté pendiente.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Stack 1/5: strict staff invitation/access-request DTOs, redacted secret input, active internal-account eligibility and exclusive expiry boundaries. Invitation management requires an existing global administrative wildcard; no new role grant.

## Validation / Validación

PASS: ten local contract/policy cases, Ruff and diff checks. No database connection or runtime migration needed.

## Limits / Límites

No routes yet. This flow targets existing internal accounts only, not public signup or learner identities. Expiry duration bounds are technical defaults for review. KAN-222 remains unresolved. / No aceptación PO ni cierre Jira.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
