# KAN-187 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **27/11/2026**. Incremento del 25/11/2026.

Define contrato y permisos de una respuesta conjunta académica, reutilizando las tres autorizaciones de agregado existentes. Nunca incorpora filas por matrícula; incluso has_data queda nulo cuando el grupo se suprime. Base de los incrementos de asistencia, entregas y competencias.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Define an aggregate-only cohort progress contract requiring all three existing academic aggregate permissions. No individual enrollment fields; suppressed groups hide record-presence flags as well as counts.

## Validation / Validación

13 offline policy/contract cases passed; Ruff and diff checks passed. No database access or API runtime added in this foundational increment.

## Limits / Límites

No new KPI formulas, risk predictions, role grants or operational model changes. Contract only until the following service/API increment. No CI wait, Jira change, merge or deployment.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
