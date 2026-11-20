# Propuesta de esquema académico mínimo / Minimal academic schema proposal

**Estado / Status:** esquema `PROPOSED`, modelos/adaptador/transacción `CODE_PRESENT_NOT_RUN` en PostgreSQL; contrato/políticas/cálculo `VERIFIED_RUNNING` solo sin BD y con fixtures sintéticos. Elizabeth confirmó revisar esta rama y **preparar contrato/código manteniendo la migración pendiente**. Borrador para acuerdo Elizabeth/Anas el **lunes 23/11/2026**, no compromiso de integración. No hay migración nueva ni ruta académica conectada a la API activa. / Code preparation authorized, migration explicitly pending. No PostgreSQL execution or mounted academic route.

**Por qué / Why:** sin estas tablas no se pueden hacer el seed académico (KAN-173), los endpoints de solo lectura (KAN-263) ni las herramientas del asistente (KAN-158, KAN-262, KAN-191). Prioridad acordada en el equipo: **primero asistencia**; entregas y competencias, después, según capacidad.

**Base existente en `dev`:** `cohort` (programa, convocatoria, fechas) y `enrollment` (persona + cohorte, `estado` `activa` / `finalizada` / `baja_voluntaria`, enlazada a la candidatura). Todo lo nuevo se vincula a ambas entidades; siguen siendo necesarias políticas explícitas por acción y cohorte. / Existing entities provide scope keys, not automatic academic authorization.

## Revisión técnica local del 19/11 / Local technical review

**Base:** `origin/dev@c59d201ddcb92ad6043bb3fad056e8a324deaea7`; propuesta original de Claude `30ade0c`. Revisión estática, no publicación ni aprobación funcional. / Static review, not publication or product acceptance.

El bloqueo está confirmado en código y Jira. La propuesta original necesita concretar cuatro invariantes antes de migrar: (1) docente aún no tiene permisos académicos en `ROLE_PERMISSIONS`; vincular tablas a cohorte no los crea; (2) la unicidad de una sesión por día pierde la sesión de medio turno exigida por KAN-55; (3) los FK individuales no impiden mezclar una sesión y una matrícula de cohortes distintas; (4) el catálogo de competencias global fijo no cumple el árbol configurable por curso y versiones de KAN-57. / Confirmed gaps: no current academic grants, missing half-session duration, cross-cohort referential integrity, and missing per-course competency/version scope.

### Incremento 1 propuesto para aprobación / Proposed first increment for approval

| Tabla / Table | Campos / Fields | Integridad / Integrity |
|---|---|---|
| `attendance_session` | UUID `id`, `cohort_id`, `session_date`, `period` (`full_day`, `morning`, `afternoon`), `duration_fraction` (1 o 0.5), `modality` (`in_person`, `online`), `created_by_user_id`, `created_at` | Única cohorte/fecha/franja; duración consistente con franja; validar fechas de cohorte; bloquear cohorte al crear y rechazar solapamiento día completo/medios turnos. / Unique cohort/date/period, consistent duration, cohort dates and serialized overlap rejection. |
| `attendance_record` | UUID `id`, `cohort_id`, `session_id`, `enrollment_id`, `status` (`present`, `full_absence`, `morning_absence`, `afternoon_absence`), `justified`, `recorded_by_user_id`, `recorded_at`, `version` | Única sesión/matrícula; FK compuestos sesión+cohorte y matrícula+cohorte; ausencia derivada 0/0.5/1, nunca dos valores independientes; estado compatible con franja. / Composite scope FKs, derived absence and period compatibility. |
| `attendance_revision` | UUID `id`, `record_id`, `version`, `status`, `justified`, `actor_user_id`, `occurred_at`, `correction_reason` | Snapshot append-only de cada versión, incluida la inicial; actor/fecha de servidor; corrección con versión esperada; registro, historial y auditoría atómicos. Motivo no va a resúmenes/asistente/logs. / Version snapshots and atomic audit, private correction reason. |

FK compuesta requiere añadir solo una restricción única `(id, cohort_id)` a `enrollment`, sin cambiar filas ni columnas. No se duplican `Program`, `Cohort`, `Person` o `Enrollment`. / Only an additional composite unique key on existing Enrollment; no duplicate entities.

**Regla de franja propuesta:** sesión completa admite los cuatro estados; sesión de mañana admite `present`/`morning_absence`; sesión de tarde admite `present`/`afternoon_absence`. Sesiones futuras no cuentan como faltas; sin fila es desconocido. Los totales de justificada y no justificada se muestran separados, sin clasificar justificadas como presencia. / Half-session statuses must match their period; future sessions excluded, missing row unknown, justification separate.

**Permisos (decisión PO 19/11/2026, preparados; rutas sin activar):** el docente de la cohorte **registra y corrige** (`attendance.record`, `attendance.correct`, `attendance.read`); **coordinación y administración consultan y corrigen** (`attendance.read`, `attendance.correct`; administración por su comodín, que también le permite registrar); el coder consulta **solo su matrícula**; captación y selección no acceden. Los permisos están en `ROLE_PERMISSIONS` para que el futuro panel de administración pueda cambiarlos. Fuera de ámbito: **403 explicado y auditado** (`attendance.access_denied`), igual que en expedientes. No se registra asistencia nueva tras una baja o fin de matrícula; las correcciones siguen permitidas con motivo. El motivo solo es obligatorio al corregir. / PO decision: teacher records and corrects; coordination and admin read and correct; learner reads own; explained and audited 403 out of scope; no new records after withdrawal; reason required only for corrections.

**Contrato de lectura:** `GET /api/v1/enrollments/{enrollment_id}/attendance-summary?date_from=...&date_to=...` y función backend `get_attendance_summary`. Devuelve periodo inclusivo, unidad días equivalentes, regla de conteo, fecha/corte, fuente, número de sesiones celebradas, registros confirmados y ausentes, duración desconocida, ausencias registradas justificadas/no justificadas y `data_state` (`no_data`, `partial`, `complete`). Totales de ausencia `null` sin registros, no cero; suma conocida explícitamente parcial cuando faltan registros. Nunca motivos, notas, SQL o URL de BD. Ámbito derivado de la matrícula y principal autenticado antes de consultar asistencia. / Read-only typed attendance summary, server-bound scope, explicit coverage and provenance.

El adaptador PostgreSQL deberá usar una transacción read-only con snapshot consistente para las consultas de matrícula/sesiones/registros; no cambiar aislamiento después de las consultas de autenticación, sino usar una conexión de lectura dedicada. Los límites de fechas son días inclusivos de `Europe/Madrid`, declarados en el DTO; el corte es timezone-aware del servidor. / Dedicated repeatable-read, read-only snapshot; explicit date timezone and server cutoff.

**Migración propuesta, todavía NO creada:** identificador único `0008`, `down_revision='0005'`. Cadena real `0001 → 0003 → 0004 → 0006 → 0007 → 0005 → 0008`; no modificar revisiones integradas. Solo estas tres tablas y restricción compuesta de matrícula; sin entregas/competencias/feedback en este incremento. Ensayo upgrade/check/downgrade exclusivamente en un contenedor PostgreSQL 16 nuevo y desechable con datos sintéticos, si Elizabeth lo autoriza. / Fresh additive successor only; no shared database migration.

### Incrementos siguientes / Following increments

- KAN-56: actividad y entregas con `cohort_id`, FK compuestos, plazos aware UTC, estado pendiente/entregado/revisado y fecha que permita derivar retraso. No ejecutar ni descargar el contenido de la entrega. Portfolio opcional con URL http(s), sin fetching. Historial de reenvío/corrección por definir con Anas.
- KAN-57: definición por programa/curso (sin herencia global), `code` y versión; rúbrica publicada inmutable; evaluación vinculada a esa versión y a una matrícula de su curso, evaluador/fecha y evidencia. C1–C10 son catálogo inicial sintético, no una restricción que impida configurar el árbol. No evaluar competencias desconocidas como nivel 0.
- KAN-173 conserva owner Abdur y revisión Yohanna hasta decisión humana. Un fixture pequeño para probar asistencia no completa ni reasigna el seed v2 de ≥100 candidaturas; el generador ML actual sigue offline y no se presenta como datos persistidos del producto.
- KAN-158 puede usar DTO/interfaz de asistencia y fixtures etiquetados mientras se aprueba el esquema; KAN-262/191 siguen dependiendo de sus incrementos. KAN-263 tiene discrepancia Jira: assignee Elizabeth, descripción David/revisión Elizabeth; aclarar sin cambiar Jira automáticamente.
- Contrato acordado, migración local validada y migración integrada son hitos distintos. El lunes 23/11 sigue siendo objetivo propuesto del contrato; no se promete integración ni se redefine congelación general del 04/12 por el corte interno mencionado del 27/11.

### Evidencia local del contrato / Local contract evidence

`api/app/modules/learning/attendance_schemas.py`, `attendance_summary.py` y `attendance_router.py`: DTO tipado, interfaz backend y handlers HTTP de resumen, creación de sesión y registro/corrección preparados. Fuente `synthetic_fixture` en pruebas; ningún fallback automático a datos de demostración. Dependencias de persistencia devuelven 503 por defecto, y el router no se importa desde `app.main`. / Prepared handlers and protocols; no automatic mock fallback or live route.

`attendance_models.py`, `attendance_policy.py`, `attendance_repository.py`, `attendance_service.py`: mapeos preparados (no importados por `app.models`), FK compuestos y restricciones, política de escritura docente, SELECTs parametrizados con proyección mínima, conexión REPEATABLE READ READ ONLY independiente y operaciones de escritura con bloqueo de cohorte, versión esperada, snapshot de revisión y auditoría sin nota. Escritura/lector deshabilitados por defecto. No se ha añadido la clave única compuesta a Enrollment todavía: requiere revisión de modelo y migración conjuntamente antes de activar las FK. El historial es append-only por el servicio, no protección frente a SQL privilegiado. / Prepared mappings/transactions only; composite Enrollment parent key is explicitly pending with migration approval.

`python -m pytest --noconftest tests/test_attendance_summary_contract.py tests/test_attendance_candidate_route.py tests/test_attendance_persistence_preparation.py -o addopts='' -q`: **60 passed**. Incluye 0/0.5/1, justificación separada, cobertura parcial, ausencia de datos, sesión futura, timestamp futuro, franja incompatible, duplicados/solapamientos, permisos positivos/negativos, revocación, matrícula propia, aislamiento de cohorte y query de ámbito falsificada; políticas de corrección, bloqueo por defecto sin tocar DB, SQL/DDL PostgreSQL compilado sin ejecutarlo y serialización HTTP sin nota privada. / Pure policy, contract, compilation and fixture checks only.

`contracts/proposed/attendance.openapi.json` exportado con `scripts/export_attendance_candidate.py`; TypeScript en `contracts/proposed/attendance.gen.ts` generado con la herramienta instalada 7.13.0. `tsc --noEmit --strict --skipLibCheck`: PASS. Contrato activo sin cambios. / Draft contract/types pass generation and type checking; live contract unchanged.

`pytest --noconftest tests/test_contract.py -o addopts='' -q`: **2 passed**, coherencia del OpenAPI activo y Bearer existentes, sin acceso a BD. / Existing live-contract consistency checks, not a running database/API certification.

**NOT_RUN/BLOCKED:** PostgreSQL académico, nueva migración, duplicados/concurrencia/rollback reales, correcciones persistidas, seed v2, interfaz, E2E y conexión del asistente. Una prueba con fixture o SQL compilado no acredita consulta/constraints de PostgreSQL. La función devuelve sumas de registros conocidos, no un histórico de exposición de matrícula: fechas efectivas de alta/baja siguen fuera del modelo Enrollment actual y deberán definirse antes de atribuir tasas de toda la trayectoria. / No database execution or lifecycle exposure claims.

## 1. Asistencia (KAN-55) — prioridad 1

Reglas del proyecto (AGENTS.md §4): presencial u online; falta completa = 1 día; media falta (mañana o tarde) = 0,5; la justificación va aparte; **no registrar no equivale a cero faltas**; todo persistido y auditado.

La tabla y política canónicas propuestas para este incremento están en «Incremento 1 propuesto para aprobación» arriba. Sustituyen el boceto original de `class_session` única por día y su permiso de escritura administrativa; esa primera aproximación no cubría sesiones de medio turno ni separaba la autoridad académica del wildcard administrativo. / The reviewed first-increment table/policy above replaces the initial daily-only sketch.

`get_attendance_summary` recibe la matrícula y el periodo; el servidor deriva la cohorte, no acepta el ámbito del modelo. Consulta individual sin endpoint agregado de coordinación en el incremento 1. / Enrollment-bound individual summary; coordination aggregation remains a later increment.

## 2. Entregas (KAN-56) — prioridad 2

| Tabla | Campos mínimos | Notas |
|---|---|---|
| `activity` | `id`, `cohort_id`, `title`, `description`, `due_at`, `created_by`, `created_at` | Actividad con plazo de la cohorte |
| `submission` | `id`, `cohort_id`, `activity_id`, `enrollment_id`, `submitted_at`, `content_url` o `content_text` (corto), `status` (`submitted`, `reviewed`) | FK compuestos de cohorte. Pendiente/retraso derivado de plazo y fecha de entrega; sin actividad no equivale a entrega pendiente. Reenvíos por acordar con Anas |

El borrador de feedback con IA (KAN-191) se guardaría aparte (`feedback_draft`: `submission_id`, `version`, texto, `status` borrador/aprobado, `approved_by`), siempre aprobado por el docente antes de publicarse. Puede quedar para un incremento posterior.

## 3. Competencias (KAN-57) — prioridad 3

| Tabla | Campos mínimos | Notas |
|---|---|---|
| `competency` | `id`, `program_id`, `code` (C1–C10 inicialmente), `name`, `version` | Configurable por curso; no heredar competencias de otro programa |
| `rubric_version` | `id`, `competency_id`, `version`, `levels` (descriptores de los niveles 1–3), `published_at`, `created_by` | Inmutable una vez publicada |
| `competency_assessment` | `id`, `enrollment_id`, `competency_id`, `rubric_version_id`, `level` (1–3), `submission_id` (opcional), `assessed_by`, `assessed_at` | Historial: una fila por valoración, nunca se sobrescribe |

## 4. Decisiones para el 23/11 / Decisions for 23/11

1. ¿La modalidad (presencial/online) va por día de la cohorte o por persona y día? Propuesta: por día, con excepción por persona si hace falta.
2. Justificación: lista cerrada de motivos sin datos sensibles (coherente con la decisión del motivo codificado de KAN-128), sin texto libre o con nota restringida.
3. ¿Entra en el MVP el borrador de feedback (KAN-191), o solo entregas?
4. Fechas por separado: **contrato mínimo acordado** (23/11) y **migraciones fusionadas** (fecha a fijar), para planificar KAN-173 y la conexión del asistente.
5. Quién implementa cada parte y quién revisa.

## English summary

Proposed minimal schema, attendance first. The reviewed first increment above defines full/half-day `attendance_session`, enrollment-bound records and immutable correction revisions, with composite cohort integrity. Academic authorization must be implemented explicitly. The enrollment-bound summary exposes coverage, unknown duration, source and freshness, never internal notes. Submission lifecycle and per-course configurable/versioned competencies remain next increments; C1–C10 are the initial synthetic catalog. Database integration/migration is pending explicit schema approval. A typed summary service with synthetic-fixture contract tests can be prepared independently; it is not PostgreSQL evidence.
