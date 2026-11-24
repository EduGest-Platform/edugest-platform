# KAN-227 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Anas; único revisor solicitado: Anasfady. Deadline Jira: **Sin duedate Jira; fecha propuesta 25/11/2026**. Incremento del 24/11/2026.

Añade Ver formaciones en el acceso público API y conecta listado/ficha/CTA con el formulario existente, fijando la convocatoria elegida. Se vuelve a contrastar con las convocatorias abiertas; una oferta retirada no provoca sustitución silenciosa. Mantiene Quiero inscribirme y el envío existente.

## EN

Implementation: Yohanna. Jira assignee: Anas. Sole requested reviewer: Anasfady.

Mount the public catalogue in API login entry and pin the chosen offer into the existing registration form. Revalidate against current open calls, block withdrawn targets and preserve ordinary registration. No automatic submission or new registration endpoint.

## Validation / Validación

19 focused Vitest cases passed; TypeScript and diff checks passed. Browser journey follows in phase 5.

## Limits / Límites

API mode only, no local seed catalogue fallback. Backend remains authoritative for withdrawals and duplicate submissions. No accounts, roles, automatic admissions or new personal fields.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
