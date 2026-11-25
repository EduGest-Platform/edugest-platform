# KAN-216 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **03/12/2026**. Incremento del 25/11/2026.

Amplía el exportador existente, sin catálogo paralelo. Corrige el ERD para dibujar una relación por restricción FK compuesta y distingue unicidad global de índices parciales. Regenera la referencia incorporando los modelos integrados, incluida acreditación documental.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Extend the existing schema reference exporter: composite FKs remain single tuple relations and partial unique indexes do not imply global one-to-one cardinality. Refresh the reference from all integrated model metadata, without connecting to PostgreSQL.

## Validation / Validación

8 offline exporter regressions passed; Ruff and diff checks passed. Reference regenerated and --check passed. No database inspection or migration execution.

## Limits / Límites

Model-only documentation, not deployed schema verification or inferred permissions/transitions. Original KAN-216 remains subject to review. No new dependencies, Jira changes, merge, deployment or CI wait.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
