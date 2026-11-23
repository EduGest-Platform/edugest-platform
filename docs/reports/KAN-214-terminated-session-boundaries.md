# KAN-214 — Terminated-session boundaries / Límites tras terminar sesión

## ES

Yohanna; único revisor solicitado: Anas. Deadline **01/12/2026**, no vencido al 23/11. Base independiente: `dev@112c33d`.

Tres escenarios de integración prueban expiración, logout y desactivación de cuenta. Antes del cambio se comprueba acceso legítimo a ocho lecturas existentes: identidad, lista/ficha, requisitos, historial de preselección y selección, silencio y auditoría. Después deben responder 401 sin mostrar el correo de la candidatura, y tres escrituras (nota, invitación, decisión) deben rechazarse sin cambiar etapa, eventos, decisiones, matrícula ni auditoría de éxito.

Una segunda sesión verifica la distinción: logout/caducidad de un token no invalidan al otro, mientras desactivar la cuenta afecta a ambos. Se usa el principal real del backend, sin bypass de dependencias. Son regresiones que amplían la comprobación actual de `/auth/me`; no cambian autenticación, permisos ni modelos.

Solo fixtures sintéticos PostgreSQL desechables. Local: Ruff, compilación Python y diff correctos. Pytest con BD no ejecutado localmente; no se espera ni verifica la finalización de CI por petición del usuario. La aceptación global de KAN-214 y su checklist de release siguen pendientes; no se cierran tareas Jira.

## EN

Owner Yohanna; sole requested reviewer Anas. Deadline **2026-12-01**, not overdue on November 23. Independent base `dev@112c33d`.

Three integration scenarios exercise expiration, logout and account deactivation across eight real protected reads and three workflow writes, after proving legitimate access. Denials must return 401 without the applicant email and preserve stage, CRM, decisions, enrollment and success-audit IDs, observed via a separate DB session.

A sibling session distinguishes token-local logout/expiry from account-wide deactivation. No auth dependency bypass, product policy, model or API change. This extends existing identity-only session checks rather than replacing them.

Local Ruff, compilation and diff checks passed; database pytest was not run locally. CI completion is deliberately not checked. Synthetic disposable fixtures only; no Jira completion or full release-checklist acceptance claimed.
