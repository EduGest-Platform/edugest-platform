# KAN-49 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **Sin duedate en KAN-49; ventana propuesta hasta 27/11/2026**. Incremento del 24/11/2026.

Acreditación explícita por administración global, con bloqueo de candidatura antes de matrícula, versión esperada y auditoría transaccional. Requiere matrícula activa, persona/cohorte/convocatoria coherentes y decisión admitida vinculada. No concede roles ni cambia admisión o acceso académico.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Record explicit global-administrator accreditation with application-before-enrollment locking, optimistic versions and transactional audit. Require a coherent active enrollment and linked final human admission; historical rows without provenance are not inferred accredited.

## Validation / Validación

20 offline policy and anonymous HTTP tests passed; Ruff and TypeScript passed. OpenAPI/client regenerated. Two PostgreSQL accreditation cases collected only; database runtime not run locally.

## Limits / Límites

No document upload, automatic formalization, UI or new permission grants. Admission remains separate; this does not implement a new academic-access gate. PostgreSQL transactions/concurrency require execution before merging. No CI wait or Jira changes.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
