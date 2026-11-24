# KAN-228 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **Sin fecha en Jira / No Jira due date**. Incremento del 24/11/2026.

Añade hilos de expediente o programa y comentarios versionados con autor y fechas. La base exige un solo ámbito por hilo y que el padre de una respuesta pertenezca al mismo hilo, con FK compuesta. Incluye migración 0016 reversible y diccionario regenerado.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Adds application/program-scoped discussion threads and versioned authored comments. Exact scope-shape checks and a composite parent FK prevent cross-thread replies. Includes reversible migration 0016 and regenerated schema reference.

## Validation / Validación

PASS: eight offline model/migration cases across discussion, staff and risk contracts, Ruff, single Alembic head, upgrade/downgrade SQL generation and diff checks. Five PostgreSQL persistence cases added but NOT RUN locally.

## Limits / Límites

Depends on #145. Persistence foundation only: no discussion routes, UI, permissions or notifications are enabled. Later services must authorize every scope, enforce edit concurrency/ancestry, audit mutations, minimize notes and render text safely. The DB prevents self-parenting, not arbitrary multi-node cycles. / Solo modelo, no colaboración funcional ni aceptación PO.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
