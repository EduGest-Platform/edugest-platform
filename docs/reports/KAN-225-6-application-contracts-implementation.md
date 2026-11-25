# KAN-225 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **Sin duedate KAN-225; historia KAN-38: 27/11/2026**. Incremento del 25/11/2026.

Continuación del flujo de invitación ya integrado: contratos y precondiciones para aplicar una solicitud aprobada. Confirmación booleana estricta con rol/ámbito exactos, cuenta interna y ficha activas, revisión distinta y rechazo de roles ya activos para no apropiarse de permisos previos.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Extend the integrated staff request flow with explicit role/scope confirmation and conservative application preconditions. Do not borrow existing role grants or treat request approval as automatic application.

## Validation / Validación

18 offline confirmation and preflight cases passed; Ruff and diff checks passed. Foundational contracts only, no database access or operational grants.

## Limits / Límites

No account creation, invitation permission changes, model/migration changes or role application in this increment. KAN-222 remains separate; no live grants, Jira changes, CI wait, merge or deployment.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
