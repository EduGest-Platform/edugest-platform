# KAN-244 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **Sin fecha en Jira / No Jira due date**. Incremento del 24/11/2026.

Stack 5/5. Añade pruebas de permisos en todas las superficies, autoría frente a otra persona del mismo ámbito, JSON/nosniff, metadatos de auditoría sin texto libre, rollback tras flush y ediciones concurrentes de la misma versión. Incluye guía bilingüe de uso y límites de la API.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Stack 5/5: adversarial scope/ownership, JSON content handling, audit privacy and rollback-after-flush, concurrent stale-write rejection and proof that discussion lifecycle does not mutate admission/enrollment. Adds a bilingual API boundary guide.

## Validation / Validación

PASS: 34 local contract, anonymous HTTP, moderation, tombstone/version and migration checks; Ruff and diff checks. All 23 PostgreSQL thread/comment/lifecycle/security cases collect successfully; none were run locally because Docker/PostgreSQL is unavailable.

## Limits / Límites

Based on #153. JSON/nosniff checks do not certify the future UI renderer against XSS; it must escape text. PostgreSQL concurrency, persistence and full authentication still require execution/review. No CI wait, merge, deployment or Jira change. / Evidencia DB pendiente y sin aceptación funcional.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
