# KAN-49 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **Sin duedate en KAN-49; ventana propuesta hasta 27/11/2026**. Incremento del 24/11/2026.

Consulta autenticada y auditada del estado documental propio o del ámbito de admisiones ya autorizado. Proyección mínima: matrícula, estado, versión y fecha; sin documentos ni identidad del verificador. Personal docente sin permiso de admisiones no recibe acceso nuevo.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Expose authenticated, audited own/admission-scope documentation reads using existing permissions. Minimize the response to enrollment ID, state, version and accreditation time; no verifier identity or document data.

## Validation / Validación

13 offline policy and anonymous HTTP tests passed; Ruff and TypeScript passed. OpenAPI and generated client updated. Two PostgreSQL scope cases collected only; database runtime unavailable locally.

## Limits / Límites

Read-only increment. Existing academic access and identity transitions unchanged; not PO acceptance or Jira Done. No local PostgreSQL execution, CI wait, merge or deployment.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
