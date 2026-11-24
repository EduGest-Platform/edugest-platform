# KAN-226 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **Sin fecha en Jira / No Jira due date**. Incremento del 24/11/2026.

GET público de lista y detalle de ofertas publicadas, con paginación acotada, filtros de programa/estado de admisión y proyección explícita sin datos internos. Borradores e identificadores inexistentes devuelven el mismo error público.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Expose published-only public course list/detail with bounded pagination, program/admission filters and explicit offer-only fields. Draft and unknown IDs share the same not-found response, including for authenticated administrators.

## Validation / Validación

24 offline tests passed, including anonymous HTTP with an empty database double (not a PostgreSQL substitute). Ruff and TypeScript passed; OpenAPI/client regenerated. Three PostgreSQL catalog cases collected only.

## Limits / Límites

Published closed calls remain visible; no date-window behavior changed. No public Program description or internal policy/counter fields. Legacy /calls filtering and direct-registration guard follow in phase 4. PostgreSQL runtime and E2E not run locally.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
