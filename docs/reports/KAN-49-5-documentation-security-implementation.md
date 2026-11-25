# KAN-49 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **Sin duedate en KAN-49; ventana propuesta hasta 27/11/2026**. Incremento del 24/11/2026.

Completa regresiones de autorización antes de acceder a datos, versiones estrictas, restricciones PostgreSQL, concurrencia y rollback de auditoría. Documenta el criterio de KAN-49, límites de formalización, privacidad y migración sin inferir decisiones históricas.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Add authorization-before-lookup and strict-version regressions, PostgreSQL constraints, concurrent-write and audit rollback cases. Document human accreditation semantics, privacy, migration and remaining product limits.

## Validation / Validación

33 offline API/schema/OpenAPI tests passed; 117 web tests passed. Ruff, TypeScript, production build and diff checks passed. All 15 PostgreSQL cases collected only, NOT executed locally. Upgrade/downgrade SQL rendered offline; no local migration/drift/E2E execution.

## Limits / Límites

No claim of PostgreSQL transaction/concurrency runtime verification. No academic-access gate, new roles, UI, document uploads, account creation or historical accreditation backfill. Jira unchanged; no merge or deployment; CI completion not awaited.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
