# KAN-126 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **Sin fecha en Jira / No Jira due date**. Incremento del 24/11/2026.

Añade regresiones de paginación con fechas empatadas, recorrido de todas las páginas sin duplicados, totales con offset fuera de rango, convocatoria ajena y filtros combinados. Comprueba parámetros inválidos sin cambiar el orden ni los permisos existentes.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Adds scoped API pagination regressions for equal timestamps, complete traversal without duplicates, out-of-range offsets preserving totals, foreign-call filtering, combined search/stage filters and invalid query parameters. Existing API behavior is unchanged.

## Validation / Validación

PASS: Ruff, Python compilation and diff checks. Eight PostgreSQL-backed cases added, NOT RUN locally because no disposable PostgreSQL is available.

## Limits / Límites

Test-only increment; no claim that KAN-126 is complete or that pagination is snapshot-isolated while new rows are inserted. PostgreSQL execution and review remain required. / Solo pruebas; sin ejecución PostgreSQL local.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
