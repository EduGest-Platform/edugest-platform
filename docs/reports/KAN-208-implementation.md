# KAN-208 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **01/12/2026**. Incremento del 24/11/2026.

Añade nosniff, DENY, no-referrer y Permissions-Policy a respuestas HTTP, incluidos errores y preflight. Las rutas API usan no-store; HSTS se añade solo en HTTPS no local según el scope ASGI, sin confiar directamente en X-Forwarded-Proto. Conserva los defaults de sesión/rate limit y rechaza configuraciones fuera de límites.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Adds security response headers, API no-store and HTTPS-only nonlocal HSTS, preserving CORS and Swagger. Retains the existing login throttle and default eight-hour session while validating TTL 1-24h, failures 1-100 and throttle window 1-1440 minutes at startup.

## Validation / Validación

PASS: 27 isolated pytest cases covering configuration, 200/401/403/404/422/500, HTTPS/local boundaries, spoofed forwarding headers, preflight and documentation compatibility; Ruff and diff checks.

## Limits / Límites

Session upper bound is an explicit technical guard for review. Existing tokens are not rotated or shortened. Login throttling remains per-process, not distributed. No TLS/CSP proxy deployment or shared environment change. Full PostgreSQL suite not run locally. / Sin despliegue ni certificación del entorno público.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
