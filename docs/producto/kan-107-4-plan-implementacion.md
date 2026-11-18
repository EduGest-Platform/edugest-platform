# KAN-107 · Entregable 4 — Plan de implementación / Implementation plan

**Estado:** revisión documental V2 del plan, sujeta a validación PO y Anas. **Instrucción obligatoria para Claude:** esta tarea no autoriza crear, editar, numerar, ejecutar, commitar ni proponer archivos de migración Alembic. El código de KAN-42 se implementará solo tras coordinación de la cadena de migraciones por la persona responsable de backend.
> **EN summary:** Design-only implementation roadmap. Form versioning and dynamic field-group access are proposed and not yet implemented. No independent Alembic revisions may be generated under KAN-107; backend coordinates schema work under KAN-42 with the current migration head and other owners.

## 1. Orden de integración y dependencias

| Paso | Qué | Responsable propuesto | Depende de | ¿Reversible? |
|---|---|---|---|---|
| **0** | Aprobar diseño de inscripción del bootcamp, política de acceso y clasificación pendiente del curso 15 h (candidatura/contacto por opción, según inventario B) y requisito de edad por convocatoria. Acordar qué asuntos legales no bloquean la **demo sintética** pero sí un uso real | PO + Anas; Melissa para requisitos reales | — | — |
| **A** | `Person`: `first_name`, `last_name` (nullable), `phone`, `birth_year`; `disponibilidad` opcional; `display_name` derivado | Backend | 0 | Sí (migración `downgrade`) |
| **B** | Diseñar integración de `form_version`, `form_version_id`, instantánea mínima y estado de publicación, sin crear migraciones desde KAN-107 | Backend / KAN-42 | A + coordinación de Alembic | Reversible según diseño real |
| **C** | API pública de formulario **sin reglas internas**; POST valida versión, convocatoria y vigencia, y admite solo respuestas permitidas | Backend / KAN-42 | B | Sí, con control de compatibilidad |
| **D** | Protección **G3/G6 por ámbito y concesión temporal**, respuestas filtradas, revocación y auditoría. Sin auto-concesión. La política/grants necesita diseño e implementación específica **dentro del trabajo de backend**; no basta `applications.read` | Backend + revisión seguridad/PO | C | Sí según pruebas |
| **E** | Formulario React desde la definición + cliente `pnpm gen:api` | Frontend (Anas) | C | Sí |
| **F** | Endurecer: `first_name/last_name` obligatorios, retirar `nombre` | Backend + Frontend | E estable | Parcial (coordinado) |

Los campos G3/G6 permanecen en la **demo sintética**, pero su divulgación requiere un control de acceso efectivo antes de considerarla funcional. Las reglas de cuotas y prioridades no están aprobadas. La Fundación y Melissa deben ratificar requisitos contractuales y finalidades antes de usar datos reales.

## 2. Cambios concretos por archivo

| Archivo | Cambio | Paso |
|---|---|---|
| `api/app/modules/identity/models.py` | `Person`: añadir `first_name`, `last_name`, `phone`, `birth_year`, luego `birth_country`, `nationality`, `gender` (D). `display_name` se calcula al guardar | A / D |
| `api/app/modules/admissions/models.py` | `Application.disponibilidad` → `nullable=True`; añadir `form_version_id` (FK), `answers` (JSON/JSONB), `privacy_notice_version`, `privacy_notice_ack_at` | A / B |
| `api/app/modules/catalog/models.py` | Nueva clase `FormVersion` (`call_id`, `version`, `status`, `definition`, `approved_by`, `approved_at`, `effective_from`) | B |
| `api/alembic/versions/` | **NO CREAR NI EDITAR desde KAN-107.** Backend deberá revisar el historial compartido y coordinar la modificación de esquema en el trabajo de implementación KAN-42, sin reservar IDs/archivos. Evitar HEADs paralelos, validar `down_revision`, compatibilidad de upgrade/downgrade | A, B, D (posterior) |
| `api/app/modules/admissions/schemas.py` | `ApplicationCreate`: `first_name`, `last_name`, `phone`, `birth_year`, `answers`, `form_version`; durante la transición acepta `nombre`; `disponibilidad: ... \| None = None`. `ApplicationDetail`: `disponibilidad: str \| None`, añade `form_version`, `answers` filtrado | A–D |
| `api/app/modules/catalog/schemas.py` + `router.py` | `FormDefinitionOut` y `GET /calls/{call_id}/form` (público, solo definición) | C |
| `api/app/modules/admissions/forms.py` (**nuevo, pequeño**) | `validate_answers(definition, answers)`: requeridos, tipos, IDs de opción, `min_selected`, `exclusive`, `excludes`. Función pura y testeable | C |
| `api/app/modules/admissions/service.py` | `create_application`: elegir versión vigente, validar con `forms.py`, **no** sobrescribir `Person` existente (H8), registrar `form_version` en `audit.record` (solo IDs) | C |
| `api/app/core/authz.py`, capa de permisos de detalle (ubicación a decidir) | El RBAC por rol+ámbito **ya existe**. Añadir en la implementación autorización por grupo G3/G6 y concesiones activas por usuario/convocatoria, **sin añadir roles nuevos** | D |
| `api/app/modules/admissions/router.py` | `get_application` devuelve `answers` **filtradas** por grupo/ámbito; `Summary` y listados carecen de G3/G6; toda lectura protegida queda auditada | D |
| `api/app/seed.py` | `form_version` v1 sintética por convocatoria + candidaturas sintéticas con `answers` | B/C |
| `contracts/openapi.json` | Regenerar con `api/scripts/export_openapi.py` (lo comprueba `test_contract.py`) | cada paso |
| `src/shared/api/schema.gen.ts` | `pnpm gen:api` (revisar diff) | cada paso |
| `src/gistar/views/api/ApiAdmissions.tsx`, `src/gistar/views/Aspirant.tsx`, `src/gistar/types.ts`, `src/gistar/seed.json` | Nombre/apellidos; formulario pintado desde `definition`; `disponibilidad` opcional; etiquetas de accesibilidad (ver Entregable 1: hallazgos de Anas) | E |
| `docs/reports/RBAC_MATRIX_*.md` | Añadir matriz de autorización por grupo/convocatoria, concesión, expiración, revocación, lectura y pruebas de no filtración | D |

**No se añaden dependencias**: validación con Pydantic/JSON estándar; sin librería de formularios dinámicos.

## 3. Conflicto de migraciones RESUELTO en el plan: propiedad única y sin reservas paralelas

**Decisión operativa de esta revisión:** KAN-107 es una **tarea documental**. **Claude no generará ninguna revisión Alembic, no propondrá nombres de archivos y no reservará números.** Los cambios de esquema del formulario y, si procede, de las concesiones de acceso se prepararán **exclusivamente dentro del desarrollo backend coordinado de KAN-42**, por Elizabeth o la persona designada por el equipo.

**Contexto comprobado:** Jira/PR #12 prevén una secuencia compartida **admisión → documentos RAG de David → académico → alertas**. En `dev` inspeccionado el 17/11 solo aparece `0001_f1_cimientos.py`; las etapas posteriores son **planificación, no migraciones ya fusionadas**.

**Procedimiento obligatorio del backend al empezar KAN-42** (no ejecutarlo ahora):

1. Revisar PRs y migraciones ya integradas y en revisión de admisión, RAG, académico y alertas, con David y la Scrum Master. Establecer un único propietario que integra la cadena.
2. Inspeccionar el estado real desde la rama limpia de trabajo: `alembic heads`, `alembic history` y los archivos existentes en `api/alembic/versions/`; con base de datos de prueba, consultar `alembic current`.
3. **Si el cambio cabe en la migración de admisión aún no compartida:** coordinarlo con su propietaria antes de fusionar, sin abrir una segunda rama de revisiones paralelas. **Si la migración ya está fusionada:** crear en ese momento una única nueva revisión encadenada al HEAD **efectivamente vigente**, previa aprobación de integración del equipo. No alterar revisiones previamente aplicadas.
4. Ejecutar `upgrade` y `downgrade` solo sobre PostgreSQL **desechable con datos sintéticos**, verificar `alembic heads` único y compatibilidad API/OpenAPI, y añadir prueba de conservación de datos históricos. Ninguna migración se ejecuta contra entornos compartidos o de producción sin autorización explícita.
5. Reservar el bloque de esquema que requieren `FormVersion`, `Application`, `Person` y, si se confirma para MVP, concesiones temporales por grupo. Ningún agente independiente puede atribuirse por su cuenta un número o modificar `down_revision`.

**Expansión y compatibilidad:** aceptar temporalmente `nombre` y `first_name/last_name`; `disponibilidad` opcional; snapshot histórico mínimo. La retirada de compatibilidad solo sucede tras validar React y API. Con datos reales nunca inferir apellidos automáticamente de `display_name`.

**EN:** No schema migrations are to be authored for KAN-107. The backend owner must coordinate any admission/form changes in KAN-42 with the single team-owned Alembic chain, inspect current heads and merge order, and test only on disposable synthetic PostgreSQL. No parallel IDs or independent migration heads.

## 4. Pruebas

Leyenda: ✅ **existe en el repositorio** (no ejecutada en esta revisión; la matriz RBAC del 13/11 las marca `CODE_PRESENT_NOT_RUN`) · 🆕 **propuesta, pendiente de escribir y ejecutar**.

| # | Criterio | Prueba | Estado |
|---|---|---|---|
| 1 | Requeridos/opcionales | Alta mínima válida (`test_applications.py::test_public_inscription_creates_person_application_event_and_audit`) | ✅ (formato actual) |
| 1 | | Falta `last_name`/`phone` → 422 con el campo; falta `disponibilidad` → 201 | 🆕 |
| 2 | Tipos y opciones | `test_validation_and_closed_calls` (formato actual) | ✅ |
| 2 | | Trim antes de longitud, solo espacios y límites tras normalización (KAN-124/#22); cambios de edad incompatibles y versionados | 🆕 |
| 2 | | Opción inexistente, `none` + otra, `short_term`+`long_term`, `min_selected=0` → 422 | 🆕 (tests unitarios de `forms.py`) |
| 2 | | Dos convocatorias con requisitos ≥18 y >16, operadores/fechas explícitos; año insuficiente en ambos; revisión humana sin aceptación/rechazo automático; teléfono y catálogo de países se validan según decisión de producto (E.164 / ISO son **propuestas**) | 🆕 |
| 3 | Versionado/conservación | Crear alta v1 → publicar v2 → leer alta: sigue `form_version=1` y mismas respuestas | 🆕 |
| 3 | | `UPDATE` de una versión `approved` falla (trigger), como `test_audit_trail_is_append_only` para auditoría | ✅ patrón / 🆕 prueba |
| 3 | | Persona reutilizada en dos convocatorias: Person no se sobrescribe; cada Application conserva sus `answers` (H8) | 🆕 (parcial: `test_same_person_reused_across_calls`) |
| 4 | Config por convocatoria | Dos convocatorias con opciones distintas de `current_situation`; opción de la A en la B → 422 | 🆕 |
| 5 | Autorización y horizontal | Captación del programa A no ve candidatura del programa B; selección limitada a su convocatoria | ✅ (`test_rbac.py::test_captacion_is_limited_to_its_program`, `test_seleccion_is_limited_to_its_call`, `test_docente_has_no_access_to_admissions`) |
| 5 | | Roles sin `applications.read` no leen expedientes ajenos; **con** `applications.read` G3/G6 siguen ocultos sin concesión del grupo y de la convocatoria; admin no hereda acceso sensible automáticamente | 🆕 |
| 5 | | `GET /applications/{id}` de otro ámbito → 403; aspirante: `/me/applications` no devuelve `answers` | ✅ parcial / 🆕 |
| 6 | Minimización y logs | `audit_event.meta` sin PII (`test_failed_login_is_audited_without_identifiers`, `test_crm_event_is_recorded_with_author_and_audited`) | ✅ |
| 6 | | Política por conjunto (auditoría, acceso/error, CRM, sesiones, exports y copias), inicio/plazo, destino y mecanismo aprobados con KAN-209/#25; ninguna purga o retención de proveedor verificada aquí | 🆕 |
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
| CA2 | Propuesta de versionado viable y comparada | ✅ Propuesta V2 documentada; revisión de integridad y de permisos pendiente |
| CA3 | Evaluación de privacidad razonada, con fuentes y decisiones pendientes | ✅ matriz V2 con fuentes oficiales enlazadas; análisis jurídico real pendiente |
| CA4 | Plan de implementación verificable por archivo y por prueba | ✅ este documento |
| CA5 | Resumen para la PO | ✅ Entregable 5 |
| CA6 | Revisión humana de PO | ⏳ Pendiente de revisión final del paquete V2 |
| CA7 | Ratificación de Melissa de las respuestas del equipo | ⏳ Pendiente (no bloquea el MVP) |

## 6. Registro de bloqueos

| ID | Bloqueo | Impacto | Dueño |
|---|---|---|---|
| B1 | **Resuelto en auditoría documental V2:** KAN-92/93/107/112 consultados el 17/11; decisiones PO en KAN-93 contrastadas | Persisten solicitudes de ratificación a Melissa, **no** inaccesibilidad de Jira | PO |
| B2 | AS-IS y aclaraciones de Melissa (Drive) no accesibles | Se usó lo citado por Anas | PO |
| B3 | **Verificación documental parcial realizada:** fuentes oficiales EUR-Lex/AEPD consultadas 17/11; sigue pendiente interpretación jurídica para datos reales | No bloquea el análisis sintético, sí cualquier declaración de cumplimiento real | Fundación / DPO |
| B4 | **Resuelto 18/11:** inventario integrado por #27 en `dev` (`d59ee8c`); #15 retiró su copia | Mantener KAN-92/93 como inventario observado canónico y KAN-107 como gobierno; acordar mínimo común y clasificación de B/C con Anas/PO | Anas / PO |
| B5 | Respuestas del equipo (17/11) pendientes de ratificar por Melissa; D1, D4, D7, D10 fuera de alcance | No bloquea el MVP | Fundación |
| B6 | Pruebas no ejecutadas en esta revisión | Las marcadas ✅ solo prueban que el código existe | Backend |

## 7. Casos de aceptación adicionales para acceso dinámico (pendientes de implementación)

1. **Concesión:** con `role_assignment` válido para la convocatoria, sin G6, `current_situation` aparece omitido/redactado; tras autorización G6 vigente de la convocatoria por admin autorizado, se muestra solo en detalle.
2. **Revocación:** revocar G6 en una sesión activa impide ver el grupo **desde la siguiente petición**, sin renovar sesión y sin posibilidad de recuperar valores mediante otro endpoint.
3. **Temporalidad:** concesión expirada o por `call_id` diferente no autoriza lectura; usuario que pierde el rol base tampoco puede leer aunque su concesión G6 no haya expirado.
4. **No auto-concesión:** una persona no puede otorgarse G3/G6 ni gestionar permisos fuera de su autoridad/ámbito; probar respuestas negativas y ausencia de side-effects.
5. **Auditoría:** alta/revocación/lectura protegida registra actor, objetivo, grupo, convocatoria, operación, instante y razón codificada, sin valores personales del formulario.
6. **Serialización:** ni listados, ni `GET /calls/{id}/form`, ni exportaciones, ni logs muestran G3/G6 sin concesión; `current_situation` se trata como grupo protegido completo, junto con certificado de discapacidad y entidad de derivación de C si se aprueban; probar ausencia de filtraciones en cada superficie.
7. **Integridad/versionado:** actualizar un permiso no cambia la versión del formulario ni respuestas históricas; una versión de otra convocatoria es rechazada.

**No declarar estas pruebas PASS hasta que haya implementación y ejecución verificadas.**

## English edition (equivalent sections, KAN-107 V2)

**Rule.** This task does not authorise creating, editing, numbering, running or proposing Alembic migrations. Backend (Elizabeth) owns the single migration chain under KAN-42 and coordinates with David (RAG) and the team; the planned order is admissions → RAG documents → academic → alerts. Only `0001_f1_cimientos.py` exists in `dev` today.

**§1 Order.** Step 0 approve design and access policy (PO + Anas; Melissa for real requirements); A `Person` fields and optional availability; B `form_version` integration design; C public form API and server-side validation; D G3/G6 protection with temporary per-call grants, revocation and audit (no self-grant); E React form from the definition + `pnpm gen:api` (Anas); F tighten required fields and retire `nombre`.

**Reconciled acceptance.** Test ≥18 and >16 requirements with explicit operators/reference dates and human review; no year-only decisions. Trim before length validation (KAN-124/#22). Protect all G6 fields including proposed C certificate status/referring entity. Align each retention class with KAN-209/#25; periods, purge and provider retention remain unverified/unapproved.

**§2–§4.** Per-file changes (with `api/alembic/versions/` explicitly "do not create or edit from KAN-107"), migration-conflict resolution (single ownership, no reserved IDs, validate real `alembic heads`), and tests.

**§5 Acceptance of KAN-107 (design task).** Dictionary with traceability ✅; versioning proposal ✅; privacy assessment ✅ (legal analysis pending); implementation plan ✅; PO summary ✅; PO human review ⏳; Melissa ratification ⏳ (does not block the MVP).

**§6 Blockers.** AS-IS/Melissa Drive documents not accessible; legal interpretation for real data pending; B4 resolved: PR #27 merged the canonical inventory into `dev`; #15 removed its copy. PO/Anas still need to agree B/C scope and routing; no code tests were run for this documentation PR.

**§7 Acceptance cases for dynamic access (not implemented, none is PASS).** Grant, immediate revocation, expiry and wrong `call_id`, no self-grant, audit without values, no leakage through lists/exports/logs, form version unchanged by permission changes.
