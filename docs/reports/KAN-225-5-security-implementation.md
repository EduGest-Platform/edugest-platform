# KAN-225 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **Sin fecha en Jira / No Jira due date**. Incremento del 24/11/2026.

Regresiones para tokens expirados, revocados y rotados; fichas inactivas; rollback tras fallo de auditoría; revisión única y ámbitos inexistentes. Documenta el orden de integración y los límites pendientes.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Add regressions for invitation invalidation, inactive profiles, audit rollback, one-time review and unknown scopes. Document integration order and remaining product boundaries.

## Validation / Validación

22 offline contract and anonymous HTTP tests passed. Ruff and diff checks passed. All 14 PostgreSQL staff cases collected successfully, not executed: no local PostgreSQL. TypeScript passed on the preceding API increment; this increment changes tests and documentation only.

## Limits / Límites

No claim of PostgreSQL runtime or concurrency validation. KAN-225 remains partial: no role application, email, account provisioning or UI. KAN-222 remains pending.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
