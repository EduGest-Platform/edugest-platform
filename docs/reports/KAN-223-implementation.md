# KAN-223 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **Sin fecha en Jira / No Jira due date**. Incremento del 24/11/2026.

Añade StaffProfile, Invitation y AccessChangeRequest con migración 0015. Las invitaciones guardan solo hash, caducidad y evidencia de uso/revocación; las solicitudes distinguen petición, revisión humana y asignación aplicada existente. Un perfil o invitación no crea permisos.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Adds staff profiles, hash-only invitation evidence and reviewed access requests, reusing existing RoleAssignment through an applied-assignment reference. Includes reversible migration 0015 and regenerated model dictionary; no role grants or activation routes.

## Validation / Validación

PASS: nine offline cases across staff/risk migration parity and authority capture, single Alembic head, upgrade/downgrade SQL generation, dictionary check and diff checks. Five PostgreSQL persistence cases added but NOT RUN locally; Ruff passed for new files.

## Limits / Límites

Depends on #144. Schema only: no token issuance, atomic one-use redemption, account creation, email or authorization endpoints. Staff eligibility, administrative reviewer authority, scope existence and permitted state transitions must be enforced by later services. KAN-222 invitation-role policy remains unresolved; no captacion invitation permission is enabled. / Solo esquema propuesto, sin conceder acceso.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
