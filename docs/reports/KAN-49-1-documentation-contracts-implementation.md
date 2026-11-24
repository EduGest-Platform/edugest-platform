# KAN-49 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **Sin duedate en KAN-49; ventana propuesta hasta 27/11/2026**. Incremento del 24/11/2026.

Primer tramo del criterio documental pendiente de KAN-49, asignada a Elizabeth. Añade estado pending/accredited, versión y evidencia de persona/fecha. Las matrículas históricas quedan pendientes; no se infiere acreditación de la admisión. Mantiene separados ciclo académico y estado documental.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Model documentary accreditation with optimistic version and actor/time evidence. Existing enrollments default to pending; admission is not documentary proof. This addresses a remaining KAN-49 criterion without duplicating the integrated admission-to-enrollment transition.

## Validation / Validación

20 offline contract, schema-drift and OpenAPI tests passed. Ruff and diff checks passed; Alembic upgrade/downgrade SQL rendered offline. PostgreSQL migration execution/drift check NOT RUN locally.

## Limits / Límites

No files, URLs, free-text notes or new personal application fields. No academic access/role/admission changes or UI. Global administration only for future write endpoints; no new role grants. Rollback removes accreditation metadata and requires preserving audit evidence. No CI wait, Jira change, merge or deployment.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
