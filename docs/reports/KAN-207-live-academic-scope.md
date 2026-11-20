# KAN-207 — Live academic scope regression / Permisos académicos vigentes

## ES

Deadline Jira: **25/11/2026**, no vencido al preparar este PR el 20/11. Base dev `5ca5194`. Dos escenarios parametrizados revocan respectivamente IA y Data, con dos tokens de docente ya abiertos, datos persistidos de ambas cohortes y controles positivos antes/después.

Tras revocar una asignación sintética: ambos tokens siguen autenticados, pero devuelven 403 al leer sesiones, resumen individual, revisiones de asistencia, competencias y evaluaciones de la cohorte revocada. También se deniegan corrección de asistencia y nueva evaluación, sin alterar registros, revisiones o evaluaciones persistidas. La otra cohorte sigue consultable. Administración conserva exactamente el historial original.

No duplica las pruebas de permisos iniciales de #67: verifica la revocación sobre sesiones activas y atraviesa ambos módulos. Revocación solo por fixture en PostgreSQL desechable; no añade un endpoint, permiso, modelo o política de revocación automática. No sustituye el futuro acceso propio del coder ni el recorrido completo de matrícula.

## EN

Jira deadline **2026-11-25**, not overdue as of preparation. Two symmetric cohort-revocation cases use two existing teacher tokens and real API-created attendance/framework/assessment data. Authentication survives, current authorization denies historical reads and writes for the revoked cohort, the other cohort remains accessible, and administrator reads prove history was not erased. Independent-session counts verify denied mutations did not persist.

No production permission/schema/API changes. Direct assignment revocation is a disposable synthetic fixture, not a new staff-management API or automatic policy. Complements initial-scope tests; it does not implement learner self-service or the full vertical flow.

## Evidence / Evidencia

Local ruff, compilation and diff PASS. Local PostgreSQL/Docker NOT RUN (unavailable); current-head CI executes the integration suite. Elizabeth primary reviewer, David secondary. No Jira update or completion claim.
