# KAN-227 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Anas; único revisor solicitado: Anasfady. Deadline Jira: **Sin duedate Jira; fecha propuesta 25/11/2026**. Incremento del 24/11/2026.

Conecta listado y ficha con lecturas del servidor, reintentos, foco de navegación y cancelación al cambiar de consulta. Solo las ofertas abiertas muestran Solicitar plaza; cargar o fallar nunca conserva un CTA obsoleto.

## EN

Implementation: Yohanna. Jira assignee: Anas. Sole requested reviewer: Anasfady.

Orchestrate server list/detail reads with retries, navigation focus and cancellation. Open offers alone show the application CTA; obsolete responses cannot publish after cancellation. Closed offers remain readable.

## Validation / Validación

16 focused Vitest cases passed; TypeScript and diff checks passed.

## Limits / Límites

Not mounted in the public entry point until phase 4. No requirements, training dates, available-seat counts or admissions guarantees are invented. No browser E2E executed yet.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
