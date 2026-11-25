# KAN-216 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **03/12/2026**. Incremento del 25/11/2026.

Completa el diccionario generado con defaults de servidor, presencia de defaults de aplicación sin evaluarlos, índices y predicados de unicidad parcial. Documenta las tuplas FK y ON DELETE/UPDATE. Orden determinista incluso con restricciones sin nombre sobre las mismas columnas.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Extend the existing generated dictionary with declared server defaults, unevaluated application defaults, index predicates and tuple FK actions. Keep deterministic ordering even for unnamed constraints sharing columns.

## Validation / Validación

16 offline exporter regressions passed; Ruff and diff checks passed on this increment. Reference regenerated; --check passed before the deterministic-order refinement and render tests cover the refinement. No database connection or callable-default execution.

## Limits / Límites

Only registered model expressions are documented, never rows or Python default results. This does not verify deployed indexes, triggers or migrations. No product rule change, Jira update or CI wait.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
