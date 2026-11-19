# KAN-148 — Requirement prefilter / Prefiltro de requisitos

**KAN-183 follow-up / Seguimiento:** the preview endpoint below still records only its access audit. A separate explicit endpoint now records immutable evaluation evidence; see [KAN-183](KAN-183-automation-executions.md). / La vista previa descrita conserva solo su auditoría; un endpoint explícito separado registra evidencia inmutable de evaluación. No equivale a entrega ni tarea resuelta.

## ES

Incremento sobre KAN-135/#49 integrado en `dev` `cf8d69a`, 19/11/2026. `POST /api/v1/applications/{id}/requirement-prefilter` evalúa una selección explícita de referencias inmutables (1–100), con `requirements.read` y el ámbito existente de la candidatura. El cliente no aporta resultados, faltantes ni actor. Referencias desconocidas/ajenas: 404; duplicadas o dos versiones del mismo código: 422.

La selección **no es un catálogo activo ni una decisión de elegibilidad**. Se devuelve `scope=explicit_versions` y `evaluation_only=true`. No se elige automáticamente la última versión ni se reinterpretan revisiones viejas. Códigos del catálogo omitidos en la selección requieren revisión humana; una lista vacía no puede aparentar que todo está cumplido. La activación de versiones por candidatura sigue fuera de alcance, como en KAN-135. Antes de usar una selección como política oficial hay que acordar y persistir esa activación.

Resultados derivados solo del servidor:

- Obligatorio sin revisión vinculada a esa definición, `pending`, `not_met` o `exception_under_review`: pendiente de revisión humana.
- `met` o `exception_approved`, vinculados a esa definición: sin señal de faltante para ese requisito. No significa admisión.
- Recomendado pendiente: aviso orientativo separado; no provoca exclusión ni sustituye una excepción humana.
- Una revisión histórica con ID de definición nulo no acredita cumplimiento: se expone como pendiente y no verificada. No se devuelve el motivo libre, nombre del revisor, etiquetas ni financiador.

Se reutiliza `automation.engine.propose` con `TaskKind.REQUIREMENTS`, usando los faltantes calculados y una huella estable de la selección. La evaluación explícita no activa la política programada de ninguna convocatoria. Solo puede devolver la propuesta `human_review` o ninguna; la ausencia de propuesta **no autoriza admisión ni acredita catálogo oficialmente completo**. Se auditan IDs y conteos, nunca motivos libres. No se cambian etapas, revisiones, historial, eventos CRM, matrículas ni se persisten tareas/ejecuciones. Los reintentos conservan clave de propuesta; cada consulta auditada es independiente, no una entrega idempotente de tareas.

Sin migración ni solapamiento con el cierre de preselección del #46. No se implementan silencio, expulsión, puntuación, valoración automática de documentos, UI, planificación periódica, outbox ni bandeja simulada. La conexión a ejecuciones persistidas sigue en KAN-183/KAN-122. No se contabiliza una propuesta como ahorro del 70 % ni se marca Jira Done.

## EN

Built on merged KAN-135/#49 at `dev` `cf8d69a` (19/11/2026). The authenticated POST evaluates 1–100 explicit immutable references under existing application scope and `requirements.read`. Results, missing evidence and actor cannot be supplied by the caller. Unknown/foreign references return 404; duplicates or multiple versions of one logical code return 422.

The response is an **explicit-version evaluation, not an active catalogue or eligibility decision**. No latest-version inference or historical reinterpretation occurs. Omitted catalogue codes require human review; an empty selection cannot appear complete. Official activation/pinning per applicant remains a separate policy/persistence contract, as in KAN-135.

Unreviewed, unbound legacy, pending, not-met or exception-under-review required items produce a human-review signal. Bound met/exception-approved results resolve that selected item only, never admission. Recommended unresolved items remain advisory. No free-text review reasons, reviewer names, labels or funder metadata are returned.

The existing requirements rule receives server-computed unresolved references and a stable selection hash. This explicit evaluation does not enable scheduled call policies. It returns only `human_review` or no proposal, never an admission/rejection result. No proposal is not evidence of an officially complete catalogue or permission to admit. Audit contains IDs/counts only. Application stage, reviews/history, CRM events and enrollment remain unchanged; tasks/executions are not persisted. Proposal keys survive retries; individual audit events are not task delivery receipts.

No migration or duplication of #46 closure/silence behavior. No automatic document assessment, scoring, expulsion, UI, periodic scheduler, outbox or simulated inbox. Persisted execution integration belongs to KAN-183/KAN-122. Proposals do not earn time-saved credit or automatically complete Jira tasks.

## Validation / Validación

Tests cover allowed/denied roles, unknown/foreign references without evaluation audit, explicit versions, omitted codes, legacy reviews, result/exception semantics, advisory separation, stable retries, no stage/CRM/enrollment/review writes and minimal audit. OpenAPI and TS client regenerated together. Local checks and actual CI results are recorded in the PR; local Docker/PostgreSQL unavailable remains NOT RUN.

Review: Elizabeth primary (human-review policy, scope/partial selection), David secondary (engine integration, stable keys, version semantics).
