# KAN-129 — Persisted reminder simulations / Simulaciones persistidas

## ES

Incremento parcial: API y PostgreSQL para simular recordatorios de documentación y ejercicios. POST `/api/v1/applications/{id}/simulated-reminders` recibe `task_ref` técnico, tipo, fecha con zona y `synthetic_only: true`; requiere `applications.crm` por ámbito. GET usa `applications.read`, límite 1–100 y total explícito. No se amplían roles.

La fecha es introducida por personal autorizado: `schedule_source=staff_entered`. No procede de un calendario validado ni demuestra que exista una tarea pendiente real. Solo se admite preselección (`enviada`, `requisitos_en_revision`); fuera devuelve 409. El motor `propose` existente decide si ha llegado el plazo usando el reloj del servidor. Antes del plazo: 200 `not_due`, sin recordatorio; en el plazo: 201; reintento: 200 con el original. El intento no vencido deja auditoría mínima.

Una clave combina la propuesta del motor y el instante de vencimiento UTC: dos zonas que representan el mismo instante deduplican; reprogramar crea otra simulación. No se repite diariamente: esta clave es distinta de la evaluación diaria KAN-183. Bloqueo de candidatura + UNIQUE + ON CONFLICT; inserción y auditoría atómicas. El historial excluye actor y clave internos, no contiene destinatario ni texto libre. `task_ref` debe ser una referencia técnica sintética, nunca un dato personal.

Tabla `simulated_reminder`: UUID, candidatura con borrado en cascada, convocatoria, referencia, tipo, vencimiento, versión de regla, clave, actor y fecha del servidor. No endpoint de edición/borrado; no se promete protección de UPDATE en BD ni una política de retención. Auditoría independiente conserva su política existente. No se modifican CRM, etapa, matrícula o decisiones.

Migración 0008 tras 0007 integrada. #46 sigue abierto con 0005 tras 0007: antes de fusionar el segundo PR hay que actualizar y reconciliar una sola cabeza Alembic, regenerar contratos y repetir pruebas. No integrar ambos sin esa reconciliación. No se reescribe ninguna migración integrada.

No scheduler, correos, inbox para aspirantes ni ahorro acreditado. Jornada informativa y entrevista quedan pendientes de fuentes de calendario/contratos; silencio permanece en #46/KAN-184. No se cambia su política ni se contabilizan estas simulaciones como trabajo completado en el evaluador del 70 %.

## EN

Partial KAN-129 increment: a scoped staff API persists documentation/exercise reminder simulations. Staff enter a synthetic technical reference and timezone-aware schedule; the response explicitly reports `simulated_only` and `schedule_source=staff_entered`. These inputs are not a verified task/calendar source. CRM permission is required to simulate; application-read permission to list. Only the two preselection stages are accepted, without granting new roles.

Existing `propose` evaluates server time: before due returns 200/not_due with no reminder; due creates 201; retry returns 200/original. An application lock, unique digest and PostgreSQL conflict handling keep recording/audit atomic. The key also includes the normalized due instant, distinguishing reschedules while deduplicating equivalent timezone offsets. Unlike daily KAN-183 evaluations, a reminder simulation does not repeat each day. Lists disclose total/limit, exclude actor/key and have no recipient or free-text message.

Migration 0008 follows integrated 0007. Pending #46 also follows 0007; whichever integrates second must reconcile the migration chain to one head, update with dev, regenerate contracts and rerun CI. No shared DB operations or rewriting of integrated migrations. Application deletion cascades to simulations, without promising audit erasure or retention policy. No update/delete API or DB update-protection claim.

No actual sends, scheduler, learner inbox, CRM/stage/enrollment decisions or savings claim. Information-session/interview calendars remain pending; silence detection stays in #46. This does not complete all KAN-129 acceptance criteria or change Jira.

## Validation / Validación

Local: ruff, Python compilation, OpenAPI/TS generation, engine unit suite and diff checks. PostgreSQL/Docker unavailable locally: NOT RUN; current-head CI is the source of DB evidence. Regression tests cover same-instant retries, rescheduling, deadline boundary, concurrent retry, atomic rollback, role/scope denial, invalid/forged fields, stage restrictions, no business writes, bounded history, application-delete cascade and migration roundtrip. Actual results are recorded in the PR.

Review: David primary for engine/deduplication and test evidence; Elizabeth for permissions, data and coordination with #46. All fixtures synthetic.
