# KAN-187 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **27/11/2026**. Incremento del 25/11/2026.

Añade GET progress-overview con asistencia agregada y periodo explícito, usando los cálculos existentes. Extrae consultas compartidas sin cambiar el contrato REST previo; aplica los tres permisos antes de consultar métricas y registra una consulta auditada.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Expose an aggregate-only cohort progress endpoint with attendance period, existing totals/missingness and suppression. Share attendance queries with the original router while preserving its helper aliases and behavior.

## Validation / Validación

23 offline contract, privacy, anonymous HTTP and attendance-period tests passed; Ruff and TypeScript passed; OpenAPI/client regenerated. Two PostgreSQL endpoint cases collected only.

## Limits / Límites

Only attendance in this increment; deliveries and competencies follow. No per-enrollment rows, model/migration changes, new formulas or role grants. No local PostgreSQL execution or CI completion wait.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
