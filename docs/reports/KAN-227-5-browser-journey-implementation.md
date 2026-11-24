# KAN-227 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Anas; único revisor solicitado: Anasfady. Deadline Jira: **Sin duedate Jira; fecha propuesta 25/11/2026**. Incremento del 24/11/2026.

Añade recorrido navegador de error/reintento, oferta cerrada, teclado/foco y solicitud fijada; lo integra en el workflow Docker E2E con repetición. Completa regresiones de cancelación y documentación bilingüe de límites y evidencias. Adapta el directorio temporal del harness a Windows/Linux.

## EN

Implementation: Yohanna. Jira assignee: Anas. Sole requested reviewer: Anasfady.

Add browser coverage for retry, closed offers, keyboard/focus and pinned application handoff; run it twice in the disposable Docker E2E workflow. Extend cancellation regressions, focus handling and bilingual evidence. Make the headless harness temporary directory portable.

## Validation / Validación

117 Vitest tests PASS; TypeScript, production build, JS syntax and diff checks PASS; 4 Python E2E-verifier regressions PASS. Built frontend + synthetic API double in headless Edge: 19/19 journey checks twice, one retained application; 2/2 responsive layout checks and visual inspection passed.

## Limits / Límites

Local browser evidence uses an API double, not PostgreSQL. Real Docker/PostgreSQL journey NOT RUN locally; CI completion not awaited. No Jira changes, merge or deployment, new dependencies, account provisioning or pending KAN-224/231 acceptance.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
