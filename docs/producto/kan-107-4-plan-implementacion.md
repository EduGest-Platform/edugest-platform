# KAN-107 · Entregable 4 — Plan de implementación / Implementation plan

**Estado:** plan **para aprobar**. Hasta la aprobación del diseño **no se tocan** modelos, migraciones, contrato ni formularios.
> **EN summary:** Six incremental, individually reversible steps (A–F) from today's `ApplicationCreate` to versioned forms. Backend (Elizabeth) owns A–D, frontend (Anas) owns E, tests/CI in each step. No new dependencies or architecture.

## 1. Orden de integración y dependencias

| Paso | Qué | Responsable propuesto | Depende de | ¿Reversible? |
|---|---|---|---|---|
| **0** | Aprobar diseño (Entregables 1–3) y resolver decisiones D1–D9 que bloqueen | PO + Melissa | — | — |
| **A** | `Person`: `first_name`, `last_name` (nullable), `phone`, `birth_year`; `disponibilidad` opcional; `display_name` derivado | Backend | 0 | Sí (migración `downgrade`) |
| **B** | `form_version` + `application.form_version_id`/`answers` + trigger de inmutabilidad + versión v0 "legado" | Backend | A | Sí |
| **C** | `GET /calls/{id}/form` y validación dinámica en `POST /applications` | Backend | B | Sí |
| **D** | Campos de G3 (origen/género) + permiso `applications.read_sensitive` + `answers` filtrado en detalle | Backend | C + **D2–D3, D6** | Sí |
| **E** | Formulario React desde la definición + cliente `pnpm gen:api` | Frontend (Anas) | C | Sí |
| **F** | Endurecer: `first_name/last_name` obligatorios, retirar `nombre` | Backend + Frontend | E estable | Parcial (coordinado) |

Pasos A–C pueden empezar con **datos no sensibles**; D queda bloqueado hasta que la Fundación resuelva D2/D3/D6.

## 2. Cambios concretos por archivo

| Archivo | Cambio | Paso |
|---|---|---|
| `api/app/modules/identity/models.py` | `Person`: añadir `first_name`, `last_name`, `phone`, `birth_year`, luego `birth_country`, `nationality`, `gender` (D). `display_name` se calcula al guardar | A / D |
| `api/app/modules/admissions/models.py` | `Application.disponibilidad` → `nullable=True`; añadir `form_version_id` (FK), `answers` (JSON/JSONB), `privacy_notice_version`, `privacy_notice_ack_at` | A / B |
| `api/app/modules/catalog/models.py` | Nueva clase `FormVersion` (`call_id`, `version`, `status`, `definition`, `approved_by`, `approved_at`, `effective_from`) | B |
| `api/alembic/versions/0002_*.py` … `0004_*.py` | Una migración por paso; `0003` crea trigger de inmutabilidad (patrón de `0001`); datos: crear `form_version` v0 y enlazar candidaturas existentes | A, B |
| `api/app/modules/admissions/schemas.py` | `ApplicationCreate`: `first_name`, `last_name`, `phone`, `birth_year`, `answers`, `form_version`; durante la transición acepta `nombre`; `disponibilidad: ... \| None = None`. `ApplicationDetail`: `disponibilidad: str \| None`, añade `form_version`, `answers` filtrado | A–D |
| `api/app/modules/catalog/schemas.py` + `router.py` | `FormDefinitionOut` y `GET /calls/{call_id}/form` (público, solo definición) | C |
| `api/app/modules/admissions/forms.py` (**nuevo, pequeño**) | `validate_answers(definition, answers)`: requeridos, tipos, IDs de opción, `min_selected`, `exclusive`, `excludes`. Función pura y testeable | C |
| `api/app/modules/admissions/service.py` | `create_application`: elegir versión vigente, validar con `forms.py`, **no** sobrescribir `Person` existente (H8), registrar `form_version` en `audit.record` (solo IDs) | C |
| `api/app/core/authz.py` | Añadir `applications.read_sensitive` a `admin` y, **según D6**, a roles concretos; el resto no | D |
| `api/app/modules/admissions/router.py` | `get_application` filtra campos `sensitivity` si falta el permiso; **listados y `Summary` nunca llevan `answers`** | D |
| `api/app/seed.py` | `form_version` v1 sintética por convocatoria + candidaturas sintéticas con `answers` | B/C |
| `contracts/openapi.json` | Regenerar con `api/scripts/export_openapi.py` (lo comprueba `test_contract.py`) | cada paso |
| `src/shared/api/schema.gen.ts` | `pnpm gen:api` (revisar diff) | cada paso |
| `src/gistar/views/api/ApiAdmissions.tsx`, `src/gistar/views/Aspirant.tsx`, `src/gistar/types.ts`, `src/gistar/seed.json` | Nombre/apellidos; formulario pintado desde `definition`; `disponibilidad` opcional; etiquetas de accesibilidad (ver Entregable 1: hallazgos de Anas) | E |
| `docs/reports/RBAC_MATRIX_*.md` | Añadir fila de `applications.read_sensitive` | D |

**No se añaden dependencias**: validación con Pydantic/JSON estándar; sin librería de formularios dinámicos.

## 3. Migraciones incrementales seguras

1. **Expand** (A, B): añadir columnas nullable / tablas nuevas; el código acepta formato antiguo y nuevo.
2. **Migrate**: poblar `first_name/last_name` a partir de `display_name` por división simple **solo en seeds sintéticos**; nunca inferir apellidos de datos reales (revisión manual).
3. **Contract** (F): obligatorios definitivos y retirada de `nombre`, cuando el frontend haya migrado y los tests pasen.
4. Cada migración con `downgrade` probado; los datos de `answers` se conservan al bajar solo si no se elimina la columna (documentar).

## 4. Pruebas

Leyenda: ✅ **existe en el repositorio** (no ejecutada en esta revisión; la matriz RBAC del 13/11 las marca `CODE_PRESENT_NOT_RUN`) · 🆕 **propuesta, pendiente de escribir y ejecutar**.

| # | Criterio | Prueba | Estado |
|---|---|---|---|
| 1 | Requeridos/opcionales | Alta mínima válida (`test_applications.py::test_public_inscription_creates_person_application_event_and_audit`) | ✅ (formato actual) |
| 1 | | Falta `last_name`/`phone` → 422 con el campo; falta `disponibilidad` → 201 | 🆕 |
| 2 | Tipos y opciones | `test_validation_and_closed_calls` (formato actual) | ✅ |
| 2 | | Opción inexistente, `none` + otra, `short_term`+`long_term`, `min_selected=0` → 422 | 🆕 (tests unitarios de `forms.py`) |
| 2 | | `birth_year` fuera de rango; `phone` no E.164; país no ISO | 🆕 |
| 3 | Versionado/conservación | Crear alta v1 → publicar v2 → leer alta: sigue `form_version=1` y mismas respuestas | 🆕 |
| 3 | | `UPDATE` de una versión `approved` falla (trigger), como `test_audit_trail_is_append_only` para auditoría | ✅ patrón / 🆕 prueba |
| 3 | | Persona reutilizada en dos convocatorias: Person no se sobrescribe; cada Application conserva sus `answers` (H8) | 🆕 (parcial: `test_same_person_reused_across_calls`) |
| 4 | Config por convocatoria | Dos convocatorias con opciones distintas de `current_situation`; opción de la A en la B → 422 | 🆕 |
| 5 | Autorización y horizontal | Captación del programa A no ve candidatura del programa B; selección limitada a su convocatoria | ✅ (`test_rbac.py::test_captacion_is_limited_to_its_program`, `test_seleccion_is_limited_to_its_call`, `test_docente_has_no_access_to_admissions`) |
| 5 | | Sin `applications.read_sensitive`: el detalle **omite** `answers` sensibles y G3; con él, los incluye; listado nunca | 🆕 |
| 5 | | `GET /applications/{id}` de otro ámbito → 403; aspirante: `/me/applications` no devuelve `answers` | ✅ parcial / 🆕 |
| 6 | Minimización y logs | `audit_event.meta` sin PII (`test_failed_login_is_audited_without_identifiers`, `test_crm_event_is_recorded_with_author_and_audited`) | ✅ |
| 6 | | Tras un alta con valores centinela (`__SENTINEL_NAT__`), `audit_event.meta` y salida de logs capturada **no contienen** los centinelas | 🆕 |
| 6 | | Agregados con grupos <5 suprimidos para campos sensibles | ✅ para etapas (`test_small_groups_are_fully_suppressed`) / 🆕 para `answers` |
| 7 | Frontend ↔ contrato | `test_committed_contract_matches_api` | ✅ |
| 7 | | `pnpm gen:api` sin diff en CI; prueba Vitest: el formulario pintado desde una definición de ejemplo envía un payload que valida contra `ApplicationCreate` | 🆕 |
| 7 | | Test de accesibilidad básica: etiquetas, "mínimo 1" en grupos de casillas, `*` + texto | 🆕 |

## 5. Criterios de aceptación de KAN-107

**Estos son los criterios de la tarea de análisis/diseño (KAN-107). La implementación se aprueba y rastrea aparte.**

| # | Criterio | Estado a fecha 17/11/2026 |
|---|---|---|
| CA1 | Diccionario consolidado con trazabilidad a modelos | ✅ Entregable 1 (pendiente de revisión humana) |
| CA2 | Propuesta de versionado viable y comparada | ✅ Entregable 2 (pendiente de aprobación) |
| CA3 | Evaluación de privacidad razonada, con fuentes y decisiones pendientes | ✅ borrador; **fuentes por verificar** (B3) |
| CA4 | Plan de implementación verificable por archivo y por prueba | ✅ este documento |
| CA5 | Resumen para la PO | ✅ Entregable 5 |
| CA6 | Revisión humana de PO | ⏳ Pendiente |
| CA7 | Respuesta de Melissa a D1–D9 | ⏳ Pendiente (bloquea Paso D) |

## 6. Registro de bloqueos

| ID | Bloqueo | Impacto | Dueño |
|---|---|---|---|
| B1 | Jira (KAN-92/93/107/112) y comentarios no accesibles desde esta sesión | No se contrastaron comentarios recientes | Yohanna / quien tenga acceso |
| B2 | AS-IS y aclaraciones de Melissa (Drive) no accesibles | Se usó lo citado por Anas | PO |
| B3 | Fuentes oficiales no verificadas en línea | Citas por revisar | DPO / equipo |
| B4 | PR #15 no integrado en `dev` | El diccionario de Anas solo existe en esa rama; este PR lo **referencia** | Anas / PO |
| B5 | D1–D9 sin respuesta | Paso D bloqueado | Melissa |
| B6 | Pruebas no ejecutadas en esta revisión | Las marcadas ✅ solo prueban que el código existe | Backend |
