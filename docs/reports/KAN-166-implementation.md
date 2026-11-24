# KAN-166 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **Sin fecha en Jira / No Jira due date**. Incremento del 24/11/2026.

Prueba la revocación mediante la API de equipo docente: tokens ya abiertos pierden acceso a equipo, asistencia, entregas y competencias de esa cohorte; otra cohorte y el rol independiente de selección se conservan. Incluye intento de auto-reincorporación denegado y reactivación autorizada sin duplicados.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Tests teaching-team revocation through the real API across existing sibling tokens, four academic surfaces, cross-cohort isolation, denied self-regrant and authorized reactivation without duplicate assignments. The independent selection role remains usable.

## Validation / Validación

PASS: Ruff, Python compilation and diff checks. Six PostgreSQL-backed cases added, NOT RUN locally.

## Limits / Límites

No grants or revocations in real environments; all mutations are disposable synthetic test fixtures. Existing last-teacher concurrency tests remain separate. / Solo fixtures sintéticos; pruebas PostgreSQL pendientes.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
