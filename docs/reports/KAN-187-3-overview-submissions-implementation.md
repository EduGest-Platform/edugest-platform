# KAN-187 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **27/11/2026**. Incremento del 25/11/2026.

Añade estados de entregas por actividad publicada reutilizando pending_submissions en modo agregado. Conserva la regla de primera entrega y revisión, evita filas de alumnado y expone as_of independiente del periodo de asistencia. Reaplica la supresión de conteos antes de serializar.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Add published-assignment delivery counts through the existing aggregate query. Keep individual rows outside the overview schema, hide counts/presence for suppressed groups and give deliveries an explicit current as_of independent of attendance date filters.

## Validation / Validación

27 offline cases passed; Ruff and TypeScript passed; OpenAPI/client regenerated. Three PostgreSQL overview parity/scope cases collected only.

## Limits / Límites

No per-learner states, submission URLs/content, new delivery formula or historical delivery window. Attendance filters apply only to attendance. No model/migration changes, database runtime or CI wait.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
