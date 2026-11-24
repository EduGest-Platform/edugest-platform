# KAN-104 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **Sin fecha en Jira / No Jira due date**. Incremento del 24/11/2026.

Prueba que dos sesiones existentes pierden acceso al revocar permisos, que la reactivación y nuevos ámbitos se reflejan sin relogin y que un permiso de cohorte no se extiende a otra. Comprueba el instante exacto de expiración con reloj controlado.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Adds regressions for immediate role revocation across sibling sessions, reactivation/new scoped grants on the same token, cohort isolation and microsecond-precise session expiry. Unlike terminated-session tests, valid sessions remain authenticated while authorization changes.

## Validation / Validación

PASS: Ruff, Python compilation and diff checks. Five PostgreSQL-backed cases added, NOT RUN locally.

## Limits / Límites

No authentication policy or product role-grant API is changed; role mutation is test setup only. PostgreSQL validation remains required. / Cambios de permisos solo en fixtures; ejecución DB pendiente.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
