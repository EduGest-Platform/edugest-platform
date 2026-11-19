# KAN-128 — Requirement reviews / Revisiones de requisitos

**KAN-135 follow-up (19/11/2026) / Seguimiento:** the original KAN-128 evidence and interim limits below are historical. Unknown or foreign-call references are now rejected on review writes; current/new history rows retain immutable definition IDs, while legacy null links remain unverified. The old “pending KAN-135” reference limitation is superseded by [the KAN-135 contract](KAN-135-call-requirements.md). / La evidencia y límites originales se conservan como historia. Las escrituras ahora rechazan referencias desconocidas o de otra convocatoria; revisión e historial nuevo conservan IDs de definición inmutable, y los vínculos nulos antiguos siguen sin verificar. El contrato enlazado sustituye la limitación anterior sobre referencias pendientes de KAN-135.

Status / Estado: implemented and tested locally (synthetic data, PostgreSQL 16 + pgvector). NOT_RUN: Docker Compose, GitHub Actions, e2e, UI. / Implementado y probado en local (datos sintéticos). No ejecutado: Docker Compose, GitHub Actions, e2e, interfaz.

## ES · Qué hace

Una persona del equipo registra el resultado de cada requisito de una candidatura (`met`, `not_met`, `exception_under_review`, `exception_approved`). **Nunca cambia la etapa de la candidatura, ni crea decisiones, ni matricula**: la decisión sigue siendo humana. Cada guardado añade una fila al historial inmutable (persona, resultado, fecha y motivo) y un evento de auditoría sin texto libre, todo en una sola transacción.

| Endpoint (`/api/v1`) | Para qué |
|---|---|
| `GET /applications/{id}/requirement-reviews` | Revisiones vigentes. Una lista vacía significa «sin revisar», nunca «todo cumplido» |
| `PUT /applications/{id}/requirement-reviews/{requirement_ref}` | Crear (201) o revisar (200) un resultado. El cuerpo lleva `result`, `reason` y `expected_version` (solo se omite al crear) |
| `GET /applications/{id}/requirement-reviews/{requirement_ref}/history` | Historial de versiones de esa revisión |

Persona y fecha las pone el servidor; un cuerpo con `reviewer` o `reviewed_at` se rechaza (422). El motivo se recorta antes de validar (1–500 caracteres). Errores: 401 sin sesión, 403 sin permiso o ámbito, 404 candidatura inexistente, 409 versión desfasada o cambio no permitido.

**Permisos** (decisión de la PO, 18/11/2026): administración, captación, selección, coordinación y docente leen y registran excepciones; aspirante y coder no tienen acceso. Solo administración, captación y selección registran `met` y `not_met`. Tomar o deshacer una excepción exige `requirements.exception`, separado de `requirements.review`. El ámbito se comprueba en el servidor: captación y selección por programa o convocatoria; el docente, por las cohortes que alimenta la convocatoria de la candidatura (en los datos de ejemplo, las convocatorias 2026B).

**Cambios de resultado permitidos:** sin revisar → `met`, `not_met` o `exception_under_review`; `met` → `not_met`; `not_met` → `met` o `exception_under_review`; `exception_under_review` → `exception_approved` o `not_met`; `exception_approved` → `not_met`. Repetir el mismo resultado con otro motivo es una enmienda.

**Límites tras la revisión del 18/11:** (1) un resultado guardado con un `requirement_ref` aún no verificado **no es una validación oficial del requisito**; la API lo indica en su descripción y el uso funcional queda bloqueado por KAN-135 (lista de requisitos por convocatoria). (2) `reason` es texto libre que ven todos los perfiles con `requirements.read` en su ámbito; un test comprueba que no sale por expedientes, listados ni auditoría. Si hay que separar motivos estructurados de detalles restringidos (grupos G3/G6 de KAN-107), es **decisión pendiente de la PO**, no se ha cambiado. (3) Los permisos de excepciones para coordinación y docente siguen la decisión de la PO recogida en el comentario de KAN-128 del 18/11; no hay otra confirmación escrita en Jira.

**Decisiones provisionales, pendientes de KAN-135:** `requirement_ref` es un identificador opaco (minúsculas, cifras, `-` y `_`, hasta 60 caracteres) sin clave foránea, porque la configuración versionada de requisitos aún no existe. Hasta entonces la API **no puede rechazar un requisito de otra convocatoria** (invariante 4 del diseño). La migración 0004 cuelga de 0003; si llega la 0002 de F2, hay que enlazarla para mantener una sola cabeza.

## EN · What it does

A team member records the result of each requirement of an application (`met`, `not_met`, `exception_under_review`, `exception_approved`). **It never changes the application stage, creates decisions or enrols anyone**: decisions stay human. Each save appends an immutable history row (person, result, date, reason) and an audit event without free text, all in one transaction.

| Endpoint (`/api/v1`) | Purpose |
|---|---|
| `GET /applications/{id}/requirement-reviews` | Current reviews. An empty list means "not reviewed", never "all met" |
| `PUT /applications/{id}/requirement-reviews/{requirement_ref}` | Create (201) or revise (200) a result. The body carries `result`, `reason` and `expected_version` (omitted only when creating) |
| `GET /applications/{id}/requirement-reviews/{requirement_ref}/history` | Version history of that review |

The server sets person and date; a body with `reviewer` or `reviewed_at` is rejected (422). The reason is trimmed before validation (1–500 characters). Errors: 401 no session, 403 no permission or scope, 404 unknown application, 409 stale version or disallowed change.

**Permissions** (PO decision, 18/11/2026): administration, recruitment, selection, coordination and teacher read and record exceptions; applicant and coder have no access. Only administration, recruitment and selection record `met` and `not_met`. Taking or undoing an exception needs `requirements.exception`, separate from `requirements.review`. Scope is checked on the server: recruitment and selection by program or call; the teacher by the cohorts the application's call feeds (in the sample data, the 2026B calls).

**Allowed result changes:** unreviewed → `met`, `not_met` or `exception_under_review`; `met` → `not_met`; `not_met` → `met` or `exception_under_review`; `exception_under_review` → `exception_approved` or `not_met`; `exception_approved` → `not_met`. Saving the same result with a new reason is an amendment.

**Limits after the 18/11 review:** (1) a result saved with a not-yet-verified `requirement_ref` is **not an official requirement validation**; the API says so in its description and functional use is blocked by KAN-135 (per-call requirement list). (2) `reason` is free text visible to every profile with `requirements.read` in scope; a test checks it does not leak through dossiers, lists or the audit log. Splitting structured reasons from restricted details (KAN-107 G3/G6 groups) is a **pending PO decision**, unchanged here. (3) Exception permissions for coordination and teachers follow the PO decision recorded in the 18/11 KAN-128 comment; there is no other written confirmation in Jira.

**Interim decisions, pending KAN-135:** `requirement_ref` is an opaque identifier (lowercase, digits, `-`, `_`, up to 60 characters) with no foreign key, because the versioned requirement configuration does not exist yet. Until it does, the API **cannot reject a requirement from another call** (design invariant 4). Migration 0004 chains to 0003; if F2's 0002 arrives, link it to keep a single head.

## Tests / Pruebas

`api/tests/test_requirement_reviews.py`: persistence in a new session; stage, events and enrolments untouched; exception recorded and seen across roles in scope; 401/403 and cross-call isolation without writes; invalid input and spoofed author/date; trim before the length limit; history kept on revision; atomic rollback when the audit write fails; stale and repeated versions; disallowed changes; exception permission separate from review; audit metadata without free text; database constraints; migration 0004 downgrade/upgrade keeping the RAG tables.
