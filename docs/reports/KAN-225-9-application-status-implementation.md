# KAN-225 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **Sin duedate KAN-225; historia KAN-38: 27/11/2026**. Incremento del 25/11/2026.

Consulta del estado para el propietario activo o administración global; verifica la asignación vinculada y muestra revocaciones sin reactivar permisos.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Expose application status to the active owner or global administrator; verify linked assignments and report revocation without regranting.

## Validation / Validación

21 offline contract/auth cases passed; Ruff passed; regenerated OpenAPI and TypeScript client.

## Limits / Límites

PostgreSQL integration cases collected only; no database runtime available locally. assignment_active reports row revocation, not effective authorization.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
