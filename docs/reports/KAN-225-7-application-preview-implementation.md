# KAN-225 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **Sin duedate KAN-225; historia KAN-38: 27/11/2026**. Incremento del 25/11/2026.

Añade una previsualización administrativa de la aplicación, con rol/ámbito solicitado y bloqueos actuales. Reutiliza elegibilidad de ficha/cuenta, revisión y existencia del ámbito; no crea ni reutiliza roles. La consulta se audita sin datos nominales.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Expose global-administration-only application preflight with the exact requested role/scope and current blockers. Preview is advisory and changes no role assignments; application will revalidate under locks.

## Validation / Validación

19 offline confirmation/policy and anonymous HTTP tests passed; Ruff and TypeScript passed; OpenAPI/client regenerated. One PostgreSQL preview case collected only.

## Limits / Límites

No role application yet; preview readiness is not a permission grant or concurrency guarantee. No tokens, accounts, migration changes, Jira updates or CI completion wait.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
