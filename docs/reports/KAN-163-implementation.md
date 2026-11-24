# KAN-163 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **23/11/2026**. Incremento del 24/11/2026.

Añade dos regresiones con quórum 2: un fallo de auditoría final revierte la segunda firma, decisión, matrícula y CRM, conservando la primera firma; un reintento puede completarse. También prueba que otra admisión puede consumir la última plaza entre firmas sin dejar una admisión parcial.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Adds two-person quorum regressions for final audit rollback, preservation of the previously committed vote, successful retry and last-place consumption by another fully signed admission. Checks decisions, enrollments, CRM and audit state together.

## Validation / Validación

PASS: pytest collection of both cases, Ruff and diff checks. PostgreSQL scenarios NOT RUN locally; no database success claim.

## Limits / Límites

Independent of the signature-authority migration PR. Test-only increment, no new decision policy or concurrency guarantees beyond existing locking. Real PostgreSQL execution remains required. / Solo regresiones, ejecución pendiente.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
