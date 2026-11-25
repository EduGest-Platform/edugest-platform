# KAN-216 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **03/12/2026**. Incremento del 25/11/2026.

Integra --check en CI, manteniendo separado el control de migraciones PostgreSQL. Prueba que comprobar no conecta a BD, crea carpetas o reescribe evidencia obsoleta. Actualiza instrucciones y comandos para regenerar la referencia cuando cambian modelos.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Require generated-reference freshness in CI independently of migration checks. Verify read-only missing/stale/invalid handling and metadata-only CLI behavior without database connections; document regeneration in contributor/agent guidance.

## Validation / Validación

31 offline exporter/schema/OpenAPI tests passed; Ruff, TypeScript, 117 web tests, production build and diff checks passed. Reference --check passed and links resolve. Coverage: 37 tables, 84 FK constraints, 30 simple text domains.

## Limits / Límites

No operational model, API or migration changes. No live-schema inspection, Mermaid image rendering or claims that linked PostgreSQL suites ran. No Jira update, merge, deployment or CI completion wait.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
