# KAN-216 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **03/12/2026**. Incremento del 25/11/2026.

El ERD deja de presentar todos los identificadores como string: usa tipos derivados del dialecto PostgreSQL y muestra las claves foráneas, incluidas las que también son primarias. Rechaza identificadores no representables en vez de generar Mermaid ambiguo.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Show PostgreSQL-derived key type tokens and explicit PK/FK attributes in the existing diagram. Fail closed on unsupported identifiers and verify every registered FK constraint has exactly one relation.

## Validation / Validación

12 offline exporter regressions passed; Ruff and diff checks passed. Reference regenerated; --check passed. All registered-model FK constraints represented once.

## Limits / Límites

ERD types are schematic; the dictionary retains full SQL types. No database access, data export, permissions inference or deployed-schema parity claim. No new rendering dependency or CI wait.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
