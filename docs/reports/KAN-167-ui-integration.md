# KAN-167 — UI integration / Integración UI

## ES

Implementación: Yohanna. Tarea asignada a Anas; único revisor solicitado: Anasfady. Deadline Jira: **26/11/2026**. Incremento del 24/11/2026.

Conecta la vista de asistencia al directorio de cohortes autorizado y a sesiones, registros y totales reales. Permite crear jornadas de 1 o 0,5 y registrar/corregir asistencia, modalidad y justificación; exige motivo al corregir. Sin dato, ausencia y agregado suprimido se mantienen separados.

## EN

Implementation: Yohanna. Jira assignee: Anas. Sole requested reviewer: Anasfady.

Connects attendance to authorized server cohorts, real sessions, records and weighted summaries. Supports creating sessions and recording/correcting attendance with modality, justification and correction reasons. Unknown, zero and suppressed totals remain distinct; API permissions and audit remain authoritative.

## Validation / Validación

PASS: TypeScript, 84 frontend tests, production build and diff checks. Added presentation regressions for half days, missing rates, true zero and suppressed aggregates.

## Limits / Límites

Depends on KAN-157 / PR #130; merge #130 first and retarget this PR to dev. Live browser/PostgreSQL end-to-end flow not run locally. Learners are identified by server enrollment UUID; no new roster or revision-history UI. / Recorrido completo no ejecutado localmente.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
