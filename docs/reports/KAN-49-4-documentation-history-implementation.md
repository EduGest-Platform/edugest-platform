# KAN-49 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **Sin duedate en KAN-49; ventana propuesta hasta 27/11/2026**. Incremento del 24/11/2026.

Retirada administrativa con versión y auditoría, sin dar de baja la matrícula. Historial paginado del estado documental con el mismo control de lectura; conserva evidencia histórica y omite identidades del verificador y metadatos ajenos.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Add administrative accreditation withdrawal without academic withdrawal, plus bounded own/admission-scope history over append-only audit events. Keep state/version/time only in the public projection to authorized readers.

## Validation / Validación

20 offline policy and anonymous HTTP tests passed; Ruff and TypeScript passed; OpenAPI/client regenerated. Three PostgreSQL lifecycle/history cases collected only, not executed locally.

## Limits / Límites

Revocation returns documentation to pending, not academic withdrawal. Existing audit records remain append-only; pending legacy rows have no fabricated history. No role changes, UI, document handling, CI wait or Jira transition.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
