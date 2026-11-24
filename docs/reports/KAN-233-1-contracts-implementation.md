# KAN-233 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **Sin fecha en Jira / No Jira due date**. Incremento del 24/11/2026.

Stack 1/5. Añade contratos estrictos de hilo, comentario, edición y resolución, control de ámbito reutilizando permisos applications.read/crm y migración 0017 para versiones de hilo y borrado lógico. Un permiso de convocatoria no da acceso a todo el programa. Todavía no expone rutas de discusión.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Stack 1/5: strict discussion DTOs, conservative existing CRM/read scope checks and migration 0017 for optimistic thread revisions and comment tombstones. Does not broaden call authority to program scope or expose discussion routes yet.

## Validation / Validación

PASS: 13 offline contract/permission/migration cases, Ruff, single Alembic head, upgrade/downgrade SQL generation and diff checks. Schema reference regenerated. No PostgreSQL migration executed locally.

## Limits / Límites

First layer of KAN-233; permissions inherit current admissions read/CRM authority, without new role grants. Staff collaboration beyond those scopes remains unavailable pending policy approval. All later stack PRs depend on this one. / Base de implementación; no cierre de Jira ni aceptación funcional.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
