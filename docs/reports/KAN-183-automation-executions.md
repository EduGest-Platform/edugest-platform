# KAN-183 — Persisted execution evidence / Evidencia persistida de ejecución

## ES

Base `dev` `e76fd6e`, actualizada el 19/11 tras revisión de David; KAN-148/#50 integrado. Este incremento registra la **ejecución de una evaluación del prefiltro**, con resultado `human_review` o `no_action`, versión de regla, etapa observada, fecha y actor del servidor, y snapshot estructurado. No acredita una tarea administrativa resuelta, entrega de recordatorio, elegibilidad ni ahorro del 70 %.

### Contrato y permisos

- `POST /api/v1/applications/{id}/automation-executions/requirement-prefilter`: recibe solo las referencias explícitas de KAN-148. El servidor recalcula el snapshot y la clave; exige `requirements.review` y ámbito. Administración, captación y selección pueden registrar según sus permisos existentes. Coordinación/docente conservan su lectura autorizada, pero no ganan escritura. Un registro nuevo devuelve 201; un reintento del mismo snapshot en el mismo día UTC devuelve 200 con el registro y fecha originales. Otro día UTC genera una evaluación nueva, incluso sin cambios de contenido.
- `GET /api/v1/applications/{id}/automation-executions`: `requirements.read` por ámbito. Orden descendente, límite 1–100 y total explícito; si hay más filas que el límite, la respuesta no es una exportación completa. No se devuelven nombre/ID del actor, motivos de revisión, etiquetas ni financiador; el actor se conserva internamente para trazabilidad.

El snapshot incluye las versiones de revisión verificadas. La clave SHA-256 canónica combina snapshot, versión de regla, etapa observada y día de evaluación UTC. El instante se obtiene una sola vez del reloj del servidor y se normaliza a UTC para clave y fecha. Ordenar las referencias no altera la clave. Cambiar evidencia/versiones o etapa crea una clave distinta, incluso si el resultado sigue siendo `no_action`. Una versión nueva de definición no se activa automáticamente. Las decisiones abiertas de KAN-148 (recomendados omitidos, activación de versiones y coordinación nominal) no se cambian en este PR.

Se bloquea la candidatura al registrar; una restricción UNIQUE y `INSERT ... ON CONFLICT DO NOTHING` protegen contra reintentos concurrentes. Registro y auditoría de creación son una transacción; un fallo de auditoría revierte ambos y permite reintentar. Los reintentos no duplican la auditoría de creación. Las lecturas de historial tienen auditoría propia. El snapshot representa los datos observados al calcular, no una reserva de tareas ni una garantía de que revisiones posteriores no cambien.

La base impide UPDATE ordinario del contenido, pero permite DELETE para no impedir borrados autorizados: la FK a candidatura usa ON DELETE CASCADE. No se añade un endpoint de borrado ni se ejecuta retención automática. Otras relaciones e historial de auditoría mantienen sus propias restricciones y decisiones de retención. No se certifica protección ante administradores/DDL/TRUNCATE ni una política de retención. No se ejecutan purgas, cambios de etapa, escrituras de revisión/CRM/matrícula, tareas programadas ni envíos. Evaluar sin disparo también deja evidencia (`no_action`). Una consulta de vista previa KAN-148 conserva su comportamiento y no crea un registro de ejecución.

La migración 0007 sigue la cabeza integrada 0006. #46 sigue pendiente: el segundo PR en integrar debe reconciliar la cadena y validar una sola cabeza, sin reescribir migraciones aplicadas ni probar sobre BD compartida. No se duplica su lógica de cierre/silencio.

Para reutilizar el cálculo se separan esquemas, loader de candidatura y servicio de prefiltro de las rutas HTTP, conservando la semántica existente. OpenAPI y cliente TS se regeneran juntos. `review_version` es un campo aditivo del prefiltro, nulo para revisiones no verificadas. La versión de regla deberá cambiar si una revisión posterior modifica su semántica.

## EN

Rebased on `dev` `e76fd6e` (19/11) after David's review; KAN-148/#50 is integrated. Records the **execution of a prefilter evaluation**, not completed administrative work, reminder delivery, eligibility or measured time savings. Each update-protected record contains rule version, observed application stage, server time/actor, structured snapshot and `human_review`/`no_action` outcome.

POST accepts only explicit references, recalculates everything server-side and requires scoped `requirements.review`. Existing admin/recruitment/selection grants apply; coordination/teachers gain no write authority. Creation returns 201; an identical same-UTC-day retry returns 200 with the original record/time. A new UTC day records a new evaluation even if the content is unchanged. Scoped GET uses `requirements.read`, descending order, bounded limit and explicit total. A truncated list is not a complete export. Actor IDs/names, review reasons, definition labels and funder metadata are excluded from responses; the recording actor remains internal for traceability.

The canonical SHA-256 key includes snapshot, rule version, stage and evaluation day in UTC. One server timestamp is normalized to UTC and used for both the key day and stored timestamp. Verified human-review versions are included, so new evidence creates a new record even if the outcome is unchanged. Reordering identical references is a retry. No automatic latest-version activation occurs. Existing KAN-148 policy questions remain unchanged. Snapshots are observations, not task reservations or promises that later reviews cannot change.

Application-row locking, a unique key and PostgreSQL conflict handling deduplicate concurrent retries. Creation and its audit are atomic; audit failure rolls back the row/key. Retries do not duplicate creation audit; history reads have their own audit. Ordinary UPDATE is blocked. DELETE remains possible for authorized erasure; the application FK uses ON DELETE CASCADE, so this table does not block application deletion. No deletion endpoint or automatic retention is introduced. Other relationships/audit history retain their own constraints and retention decisions. This is not administrator/DDL/TRUNCATE protection. No retention policy, purge, stage/review/CRM/enrollment mutation, periodic scheduler, inbox or external sending. No-trigger evaluations are recorded as `no_action`; the existing preview endpoint does not record executions.

Migration 0007 follows integrated 0006. Pending #46 must be reconciled by whichever PR integrates second, preserving one head and avoiding changes to applied migration history/shared DB operations. No closure/silence duplication. Shared calculation moves out of HTTP routes, models into schemas and the application loader into the service layer. OpenAPI/TS regenerate together; `review_version` is additive and null for unverified legacy reviews. Bump the rule version when future semantic changes occur.

## Validation / Validación

Focused tests: persistence across sessions; stable retry IDs/timestamps; changed review versions; no-action evidence; concurrent retries; audit rollback; positive/negative role/scope; forged fields; no business-state writes; update protection and application-delete cascade; UTC-day boundaries including offset timestamps; legacy snapshot reads; minimal audit; limited-list totals; migration roundtrip preserving requirements/RAG. Existing KAN-148 tests guard the shared-calculation refactor. Actual local/CI results are recorded in the PR. Local Docker/PostgreSQL unavailable remains NOT RUN. No Jira changes or task-completion claim.

Review: David primary (idempotency/concurrency and engine evidence), Elizabeth secondary (permissions, schema, migration and evidence meaning).

## Historical compatibility / Compatibilidad histórica

Snapshots are returned as stored JSON objects, not revalidated as the current PrefilterResult. The rule_version remains available for interpretation; old objects may lack new fields. POST still accepts only references and computes snapshots server-side. / Los snapshots se devuelven como objetos JSON almacenados, sin exigir el PrefilterResult actual. rule_version permite interpretarlos; pueden faltar campos recientes. El POST sigue aceptando solo referencias y calculando el contenido en el servidor.
