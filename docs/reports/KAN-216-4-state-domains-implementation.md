# KAN-216 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **03/12/2026**. Incremento del 25/11/2026.

Añade índice de CHECK simples IN con valores textuales y conserva las expresiones compuestas completas sin interpretarlas. Documenta fuentes de transición/autorización y diferencias entre publicación/admisión, matrícula/acreditación e invitación/acceso.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Index complete simple text IN checks, decoding SQL-escaped quotes while preserving compound predicates without interpretation. Link stored vocabularies to actual service/test sources; no workflow or permission is inferred from database values.

## Validation / Validación

19 offline exporter regressions passed; Ruff and diff checks passed. Reference regenerated and --check passed. All state-boundary document links resolve.

## Limits / Límites

The text-domain index is deliberately partial, not a SQL parser or workflow specification. Omitted fields can have compound/API-only rules. No database, migration or domain acceptance claim; no CI wait.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
