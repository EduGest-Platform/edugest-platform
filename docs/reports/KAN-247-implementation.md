# KAN-247 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **Sin fecha en Jira / No Jira due date**. Incremento del 24/11/2026.

Corrige la clasificación de entregas y el indicador late durante la hora repetida del cambio de horario: compara instantes UTC, conserva el límite inclusivo existente y la primera fecha de entrega. Las fechas sin zona se rechazan, sin asumir la del equipo.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Normalizes deadline comparisons to UTC instants for delivery state and serialized late flags. Preserves inclusive equality and first-submission semantics, rejecting unknown timezones rather than assuming the host timezone.

## Validation / Validación

PASS: 11 offline regressions, Ruff and diff checks. Three repeated-hour cases failed on the previous implementation and pass after the fix; boundary, equivalent-offset, resubmission and naive-date cases pass. No PostgreSQL/browser run locally.

## Limits / Límites

No new deadline policy, stored-data migration or model integration. PostgreSQL normally returns UTC; the fix also protects valid localized in-memory values. Existing duplicate-delivery/scope API tests remain separate. / Sin cambio de política ni migración.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
