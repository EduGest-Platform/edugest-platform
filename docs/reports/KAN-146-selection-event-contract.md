# KAN-146 — Selection events and timing contract

Owner: Yohanna. Cross-review: Anas (Jira), Elizabeth (PO/backend). David: elapsed-time semantics and automation boundary. Status: **PROPOSED**, not an implemented API or an approved PO policy. Inspected base: dev c59d201 (including integrated #46), 19/11/2026.

## ES — Qué existe y qué falta

El CRM integrado acepta `contacto`, `nota`, `recordatorio`; registra fecha y actor del servidor, pero no una cita estructurada. `Stage` contiene `convocada` y `evaluacion_en_curso`: un literal no demuestra un flujo de citaciones implementado. Los campos de jornada/entrevista de `src/gistar/seed.json` son del prototipo, no una fuente PostgreSQL validada.

El motor integrado distingue `information_session` de `interview`: la jornada informativa usa una ventana ANTERIOR a la fecha; la entrevista usa actualmente vencimiento + retraso. No reutilizar la rama de entrevista como aviso previo sin decisión explícita y pruebas. `information_session` tampoco equivale a jornada de selección. KAN-129/#57 propone simulaciones de documentación/ejercicios; no aporta calendario de entrevistas. #46 ya integrado permite convocar a selección, retirada expresa y silencio confirmado/reprogramado mediante decisión humana. Convocar termina la preselección, pero no crea una cita estructurada ni sustituye este contrato.

## ES — Contrato propuesto para KAN-155

Una cita es una entidad distinta del historial CRM y de una decisión de admisión. El siguiente vocabulario es una propuesta; NO se añade a `EventCreate`, OpenAPI ni al modelo actual en este PR.

| Campo propuesto | Regla y finalidad |
|---|---|
| `id`, `application_id`, `call_id` | UUID generado y ámbito derivado en servidor; nunca aceptar convocatoria incoherente con candidatura. |
| `kind` | `selection_day` o `individual_interview`; no confundir con jornada informativa. |
| `starts_at`, `ends_at` | Instantes conscientes de zona, normalizados a UTC; fin estrictamente posterior al inicio. |
| `display_timezone` | Zona IANA validada para presentar fecha/hora; no sustituye al instante UTC. |
| `status` | `scheduled`, `cancelled`, `completed`; asistencia/resultados siguen pendientes de contrato separado. |
| `version` | Entero de concurrencia; reprogramar/cancelar exige versión observada. |
| `created_at`, `updated_at`, actor interno | Servidor; no admitidos como entrada del cliente. |
| `policy_version` | Versión de la política aprobada aplicada; no adoptar automáticamente una versión nueva. |

No recoger texto libre de conclusiones, puntuaciones, salud, enlaces de videollamada con tokens ni destinatarios en este contrato mínimo. Esos datos requieren minimización, permisos y retención explícitos antes de ampliar KAN-155. Un ID de cita es referencia operativa, no prueba de asistencia.

### Operaciones y coherencia propuestas

1. Crear una cita exige permiso de acción y ámbito verificados antes de leer/escribir datos protegidos. Elizabeth debe acordar permisos concretos: no asumir que CRM autoriza citaciones o que cinco perfiles pueden editarlas.
2. Crear con clave idempotente repite el mismo resultado; misma clave con payload diferente devuelve conflicto. Clave vinculada a ámbito, actor/operación y revisión de cita, no reutilizada como evidencia de entrega.
3. Reprogramar conserva identidad, incrementa versión y guarda historial mínimo. Dos clientes sobre la misma versión: solo uno gana; el otro recarga (409 propuesto). No sobrescribir silenciosamente.
4. Cancelar conserva evidencia mínima y anula futuros avisos de esa versión. Un trabajo ya preparado debe volver a verificar estado/versión antes de generar/enviar; aún no hay worker implementado.
5. Completar una cita no admite ni descarta ni matricula. Ausencia y silencio producen revisión humana; ningún vencimiento decide automáticamente.
6. Cita/historial/auditoría deben ser atómicos. Errores 401/403/404/409/422 siguen las convenciones de la API; no exponer existencia fuera del ámbito autorizado.

### Márgenes parametrizables propuestos

| Parámetro | Semántica | Decisión pendiente |
|---|---|---|
| `reminder_lead_seconds` | Ventana previa: `starts_at - lead <= now < starts_at`. Con cero, ventana vacía; no inventar un envío inmediato. | PO decide si permitir cero para desactivar o exigir bandera separada. |
| `followup_grace_seconds` | Tiempo transcurrido desde fin de cita antes de proponer revisión humana. | Activación, valor y roles de confirmación pendientes. |
| `policy_version` | Fija los márgenes con los que se evaluó una cita. | Alcance por convocatoria y mecanismo de aprobación pendientes. |

Sin valores por defecto inventados ni umbrales de 24/48 horas atribuidos a Melissa. Duraciones no negativas y acotadas antes de implementar; límite superior pendiente de PO. Hacer aritmética en UTC para tiempo transcurrido, también al cambiar de hora. Si el negocio quiere «día laborable» o «misma hora local mañana», necesita una regla/calendario separado: no equivale a sumar segundos.

Ejemplo sintético, no política aceptada: inicio `2026-10-25T01:30:00Z`, lead 3600 s; ventana `[00:30Z, 01:30Z)`. En Europe/Madrid atraviesa la hora repetida: comparar instantes UTC, no solo la etiqueta local «02:30». Reprogramar a otro instante invalida propuestas de la revisión anterior. No inferir timezone por navegador o localidad.

### Matriz de pruebas para la futura implementación

| Caso | Resultado exigido |
|---|---|
| `now` antes, justo al inicio de ventana y justo al inicio de cita | Sin aviso / propuesta / sin aviso previo obsoleto. |
| Offset distinto, mismo instante | Misma identidad temporal, sin duplicado. |
| Cambio de hora de primavera y otoño | Duración transcurrida estable; sin segunda propuesta por hora repetida. |
| Fecha sin zona, fin <= inicio, duración negativa | Rechazo sin mutación/auditoría de éxito. |
| Cancelación/reprogramación tras preparar aviso | Revalidar versión; no usar la propuesta anterior. |
| Dos modificaciones concurrentes, reintento idéntico y clave reutilizada con cambios | Una versión ganadora; reintento estable; conflicto explícito. |
| Rol o convocatoria ajena, aspirante/coder | Denegar escritura y no filtrar conclusiones/historial interno. |
| Error al auditar | Rollback de cita y cambio de estado. |
| Cita completada, ausencia o gracia agotada | Ningún cambio automático a admitida/no_admitida/matrícula. |

### Decisiones necesarias antes de programar KAN-155

Anas valida estados/errores necesarios para la UI. Elizabeth decide permisos, etapas habilitadas, solapamientos de citas, política de cancelación, márgenes, retención y alcance por convocatoria. David revisa que las ventanas no contradigan el motor actual y que #26 siga protegiendo cambios de hora. El equipo confirma contrato antes de añadir rutas, tablas o pantallas. Este PR entrega una propuesta revisable, no aceptación de negocio ni cierre de Jira.

## EN — Canonical meaning of the proposal

The integrated CRM stores contact/note/reminder events, not structured appointments. Stage literals and prototype seed fields do not prove a calendar flow. The existing engine distinguishes a pre-event information-session window from an interview reminder after due+delay; neither represents an approved selection-day contract. Integrated #46 implements human decisions to call to selection, withdraw, confirm silence or postpone silence review. Calling ends preselection but does not create a structured appointment. #57 remains a separate reminder-simulation PR for documentation/exercises.

Propose a distinct appointment with server ID/scope, `selection_day` or `individual_interview`, aware UTC start/end, validated IANA display zone, scheduled/cancelled/completed state, optimistic version, server actor/timestamps and approved policy version. End must follow start. No interview conclusions, scores, sensitive notes, tokenized meeting links or recipient data in the minimum contract. This is NOT added to OpenAPI or persistence by this documentation PR.

Authorization is action+scope, with exact permissions pending PO approval. Creation idempotency is scoped and payload-bound; changed payload with a reused key conflicts. Reschedule preserves identity and records a new version/history; stale updates conflict. Cancelled/rescheduled appointments invalidate old reminder proposals, which must recheck version before execution. Appointment completion, absence or expired grace must never admit, reject or enroll a person. Mutation/audit must be atomic and follow existing API error conventions.

Proposed nonnegative bounded margins: pre-event lead (`start-lead <= now < start`), post-end follow-up grace (human review only), and explicit policy version. No default values, upper bound or activation rule are accepted here. Zero lead creates an empty window; PO must choose whether it disables reminders or needs a separate flag. Durations mean elapsed UTC time, not business days or wall-clock calendar arithmetic. Synthetic DST example: start 2026-10-25T01:30Z and 3600s lead gives [00:30Z,01:30Z), regardless of repeated local hour in Madrid.

Future tests must cover exact boundaries, equivalent offsets, spring/fall DST, naive/invalid dates, cancellation/reschedule revalidation, concurrent stale writes, retries/key conflicts, negative role/scope, atomic audit rollback and no automatic decisions. Anas validates UI needs; Elizabeth accepts permissions, stages, overlaps, cancellation, margins and retention; David reviews engine/DST consistency. No executable change, Jira mutation, deployment or business-policy acceptance is claimed.

## Sources and validation / Fuentes y validación

- [CRM schemas](../../api/app/modules/admissions/schemas.py), [router](../../api/app/modules/admissions/router.py), [engine](../../api/app/modules/automation/engine.py), [DST tests](../../evals/automation/test_dst_deadlines.py).
- [CRM policy](KAN-120-crm-event-policy.md), [Jira KAN-146](https://anasfady87-1789923749606.atlassian.net/browse/KAN-146), [integrated #46](https://github.com/EduGest-Platform/edugest-platform/pull/46), [draft #57](https://github.com/EduGest-Platform/edugest-platform/pull/57).
- Integrated preselection evidence: [service](../../api/app/modules/preselection/service.py), [routes](../../api/app/modules/preselection/router.py), [tests](../../api/tests/test_preselection_closure.py).
- Local validation: relative source links and whitespace; no API/DB test required for documentation-only proposal. Future test matrix above is NOT executed evidence.
