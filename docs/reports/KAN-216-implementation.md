# KAN-216 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **03/12/2026**. Incremento del 24/11/2026.

Aporta ERD y diccionario bilingüe reproducibles desde los modelos SQLAlchemy: tablas, claves foráneas, tipos PostgreSQL, nulabilidad, unicidad y vocabulario de estados CHECK. Incluye generador y modo --check; no lee filas ni conecta a una base. Incluye las tablas propuestas en KAN-171 y por eso depende de #134.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Adds a reproducible bilingual model ERD and PostgreSQL dictionary with tables, foreign keys, exact types, nullability, uniqueness and CHECK state vocabulary. Includes deterministic generator and stale-document checking, without row data or DB connections. Based on #134 to cover its new schema.

## Validation / Validación

PASS: generator and --check across independent processes, five offline tests (three dictionary regressions and two model/migration parity tests), Ruff, source-link and diff checks.

## Limits / Límites

Depends on PR #134. This is a code-derived schema reference, not a live database certification, permission matrix or PO acceptance. Composite business cardinality is not inferred. PostgreSQL migration execution remains not run locally. / Referencia de código; no certifica una base migrada ni permisos.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
