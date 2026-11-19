# Propuesta de esquema académico mínimo / Minimal academic schema proposal

**Estado / Status:** `PROPOSED`. Borrador para que Elizabeth (backend, KAN-55 y KAN-57) y Anas (frontend, KAN-56) lo acuerden el **lunes 23/11/2026**. No hay migración, modelo ni endpoint: no se crea ninguna migración hasta que se apruebe. Solo datos sintéticos. / Draft for the 23/11 agreement; no migration, model or endpoint is created until it is approved.

**Por qué / Why:** sin estas tablas no se pueden hacer el seed académico (KAN-173), los endpoints de solo lectura (KAN-263) ni las herramientas del asistente (KAN-158, KAN-262, KAN-191). Prioridad acordada en el equipo: **primero asistencia**; entregas y competencias, después, según capacidad.

**Base existente en `dev`:** `cohort` (programa, convocatoria, fechas) y `enrollment` (persona + cohorte, `estado` `activa` / `finalizada` / `baja_voluntaria`, enlazada a la candidatura). Todo lo nuevo cuelga de `enrollment` y de `cohort`, para que el ámbito «docente de su cohorte» ya funcione con el control de acceso actual.

## 1. Asistencia (KAN-55) — prioridad 1

Reglas del proyecto (AGENTS.md §4): presencial u online; falta completa = 1 día; media falta (mañana o tarde) = 0,5; la justificación va aparte; **no registrar no equivale a cero faltas**; todo persistido y auditado.

| Tabla | Campos mínimos | Notas |
|---|---|---|
| `class_session` (día lectivo) | `id`, `cohort_id`, `session_date`, `modality` (`presencial`/`online`), `created_by`, `created_at` | Única por (`cohort_id`, `session_date`). Permite distinguir «sin registro» de «sin faltas» |
| `attendance_record` | `id`, `session_id`, `enrollment_id`, `status` (`presente`, `falta_completa`, `falta_manana`, `falta_tarde`), `justified` (bool), `justification_code` (lista cerrada, opcional), `recorded_by`, `recorded_at`, `version` | Única por (`session_id`, `enrollment_id`). El valor (0 / 0,5 / 1) **se calcula** del `status`; no se guarda dos veces |
| `attendance_revision` (append-only) | `id`, `record_id`, `version`, `status`, `justified`, `justification_code`, `reason`, `actor_user_id`, `occurred_at` | Cada corrección deja la versión anterior, con persona, fecha y motivo. Mismo patrón que `requirement_review_revision` |

**Permisos propuestos:** registrar y corregir: docente de la cohorte y administración (`attendance.record`). Leer: además coordinación (agregado). El coder ve solo lo suyo.

**Consulta para el asistente y KAN-263** (solo lectura, ámbito comprobado en FastAPI antes de leer): `get_attendance_summary(cohort_id, enrollment_id?, from, to)` devuelve días de falta (suma de 1 y 0,5), justificadas frente a no justificadas, sesiones con registro, **sesiones sin registro**, el periodo y la fecha del último registro. Si no hay datos, lo dice; nunca devuelve un cero inventado.

## 2. Entregas (KAN-56) — prioridad 2

| Tabla | Campos mínimos | Notas |
|---|---|---|
| `activity` | `id`, `cohort_id`, `title`, `description`, `due_at`, `created_by`, `created_at` | Actividad con plazo de la cohorte |
| `submission` | `id`, `activity_id`, `enrollment_id`, `submitted_at`, `content_url` o `content_text` (corto), `status` (`entregada`, `fuera_de_plazo`) | Única por (`activity_id`, `enrollment_id`). «No entregada» se calcula: plazo vencido y sin fila |

El borrador de feedback con IA (KAN-191) se guardaría aparte (`feedback_draft`: `submission_id`, `version`, texto, `status` borrador/aprobado, `approved_by`), siempre aprobado por el docente antes de publicarse. Puede quedar para un incremento posterior.

## 3. Competencias (KAN-57) — prioridad 3

| Tabla | Campos mínimos | Notas |
|---|---|---|
| `competency` | `id`, `code` (C1–C10), `name` | Catálogo fijo para la demo |
| `rubric_version` | `id`, `competency_id`, `version`, `levels` (descriptores de los niveles 1–3), `published_at`, `created_by` | Inmutable una vez publicada |
| `competency_assessment` | `id`, `enrollment_id`, `competency_id`, `rubric_version_id`, `level` (1–3), `submission_id` (opcional), `assessed_by`, `assessed_at` | Historial: una fila por valoración, nunca se sobrescribe |

## 4. Decisiones para el 23/11 / Decisions for 23/11

1. ¿La modalidad (presencial/online) va por día de la cohorte o por persona y día? Propuesta: por día, con excepción por persona si hace falta.
2. Justificación: lista cerrada de motivos sin datos sensibles (coherente con la decisión del motivo codificado de KAN-128), sin texto libre o con nota restringida.
3. ¿Entra en el MVP el borrador de feedback (KAN-191), o solo entregas?
4. Fechas por separado: **contrato mínimo acordado** (23/11) y **migraciones fusionadas** (fecha a fijar), para planificar KAN-173 y la conexión del asistente.
5. Quién implementa cada parte y quién revisa.

## English summary

Proposed minimal schema, attendance first. Attendance: `class_session` per cohort day (so "no record" differs from "no absence"), `attendance_record` per enrolment and day (present, full absence = 1, morning/afternoon absence = 0.5, justification kept separate), and an append-only `attendance_revision` for audited corrections. Submissions: `activity` with a due date and `submission` per enrolment ("not submitted" is derived). Competencies: C1–C10, immutable `rubric_version` with levels 1–3, and an assessment history. Every table hangs from `cohort`/`enrollment`, so teacher-cohort scoping works with today's access control. The read-only `get_attendance_summary` tool reports the period, missing records and freshness, and abstains when there is no data. Nothing is implemented; decisions for 23/11 are listed above.
