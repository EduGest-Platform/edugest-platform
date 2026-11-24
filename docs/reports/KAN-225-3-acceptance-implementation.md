# KAN-225 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **Sin fecha en Jira / No Jira due date**. Incremento del 24/11/2026.

Stack 3/5. Una cuenta interna autenticada puede consumir solo su invitación válida y activar su ficha. La aceptación comprueba propiedad, caducidad, uso/revocación y estado de cuenta/ficha bajo los mismos bloqueos que renovación/revocación. Incluye consulta de la ficha propia; no modifica roles.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Stack 3/5: authenticated, account-bound single-use acceptance and own-profile reads. Profile/invitation locking serializes acceptance with renewal/revocation; unknown, foreign, expired and consumed tokens share a generic unavailable response. Activation does not grant roles.

## Validation / Validación

PASS: 15 local contract/policy/anonymous HTTP cases, Ruff, TypeScript and diff checks. OpenAPI/client regenerated. Two PostgreSQL acceptance cases added, NOT RUN locally.

## Limits / Límites

Based on #157. Activates only an existing internal-account profile, not a new login account or learner identity. No privilege grants or notifications. PostgreSQL race/persistence evidence remains pending. / No completa onboarding de cuentas nuevas.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
