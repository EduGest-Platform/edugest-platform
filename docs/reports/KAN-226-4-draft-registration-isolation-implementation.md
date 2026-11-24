# KAN-226 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **Sin fecha en Jira / No Jira due date**. Incremento del 24/11/2026.

Filtra borradores también en /calls y deniega inscripciones directas en ofertas no publicadas antes de crear persona o candidatura. La inscripción comparte bloqueo de convocatoria con la retirada administrativa. Las candidaturas ya existentes conservan su historial y permisos.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Exclude drafts from legacy /calls and reject direct registration before person/application writes. Registration and publication changes share the call lock. Existing application history and scoped access remain available.

## Validation / Validación

26 offline tests passed, including real registration-service rejection before writes using a lookup-only database double. Ruff passed; OpenAPI/client regenerated and TypeScript passed. Three PostgreSQL registration cases collected only.

## Limits / Límites

Unknown and unpublished call IDs now share public_course_not_found/404 for registration. Published closed calls retain the existing registration rejection. No date-window policy change, automatic admission or shared database operation. PostgreSQL concurrency and E2E NOT RUN.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
