# KAN-107 · Entregable 2 — Versionado del formulario por convocatoria / Per-call form versioning

**Estado:** revisión documental V2 para aprobación PO/Anas. Ningún modelo, migración ni contrato modificado. **Norma para todo el equipo (personas y agentes de IA): bajo KAN-107 no se crean migraciones ni se reservan números de revisión**; coordinación por la responsable de backend en KAN-42.
> **EN summary:** One new table (`form_version`) holding an immutable, approved JSON definition per call; each application stores `form_version_id` and its `answers` as stable option IDs. Chosen over YAML-in-repo and over a fully relational field/option model.

## 1. Requisitos y cómo se cumplen

| Requisito | Cómo |
|---|---|
| Versión identificable por convocatoria | `form_version(call_id, version)` único |
| La candidatura conserva su versión | `application.form_version_id` fijado al crearla, no modificable |
| Cambios posteriores no alteran respuestas | Versiones **aprobadas inmutables** (trigger, igual patrón que `audit_event_append_only` en `0001_f1_cimientos.py`); respuestas guardan **IDs**, no etiquetas |
| IDs estables de campos y opciones | `field.id` y `option.id` en snake_case, nunca reutilizados ni renombrados; solo se añaden o se marcan `retired` |
| Quién aprueba y cuándo entra en vigor | `approved_by` (FK `app_user`), `approved_at`, `effective_from` |
| Sin duplicar estructuras | 1 tabla nueva + 1 FK + 1 columna JSONB |
| Requisito de edad por convocatoria | Edad al inicio del curso; bootcamp mayoría de edad, B `gte` 16; año insuficiente → revisión humana. PO 19/11, diseño no implementado |

**Evidencia de alcance:** inventario KAN-92/93 integrado en dev. PO 19/11: B, fecha concreta → candidatura por `call_id`; organizar/avisar → solicitud de contacto. C fuera del MVP. El versionado no convierte contactos en candidaturas.

## 2. Comparativa breve

| Criterio | A. JSON/YAML versionado **en el repositorio** | B. Tablas relacionales (`form_field`, `form_option`, `form_version`…) | **C. Recomendada: 1 tabla `form_version` con definición JSON en BD** |
|---|---|---|---|
| Tablas nuevas | 0 | 3–4 | **1** |
| Coste de cambios de esquema | Bajo, pero referencia sin FK | Alto (tablas y joins) | Bajo-medio (**coordinar dentro de la cadena de Alembic del equipo; ninguna migración autorizada aquí**) |
| Cambiar opciones de una convocatoria | Requiere PR + despliegue | Posible sin despliegue | **Posible sin despliegue** |
| Traza de aprobación | Git (autor de PR), no vinculada a la BD | Sí, en BD | **Sí, en BD (`approved_by/at`)** |
| Integridad referencial candidatura→versión | No | Sí | **Sí (FK)** |
| Validación en API | Carga de fichero | Consultas | **Carga de una fila; validador Pydantic dinámico** |
| Riesgo de sobreingeniería | Bajo | **Alto** | Medio: requiere controles de publicación y vigencia |

**Recomendación única para el MVP: opción C.** Mantiene integridad (FK + inmutabilidad), da trazabilidad de aprobación y no obliga a desplegar para cambiar las opciones por convocatoria (decisión de la PO). Un cambio a tablas relacionales solo se justificaría si aparecen consultas SQL frecuentes sobre opciones, algo que hoy no existe.

## 3. Esquema conceptual

```
call 1 ──< form_version >── 1 app_user (approved_by)
              │ id (uuid)
              │ call_id        FK call.id
              │ version        int, UNIQUE(call_id, version)
              │ status         'draft' | 'approved' | 'retired' (estado operativo)
              │ definition     JSONB   ← campos, opciones, reglas
              │ approved_by    FK app_user (nullable en draft)
              │ approved_at    timestamptz
              │ effective_from timestamptz
              │ created_at
              │
application >── form_version_id FK (NOT NULL en altas nuevas)
              answers JSONB   {"current_situation": ["long_term_unemployed"], ...}
```

Reglas:
1. El backend elige la versión **publicada y vigente para esa misma `call_id`**; no confía en una versión enviada por el navegador. Una versión inicializada previamente solo se admite si la política de ventana de compatibilidad la autoriza explícitamente para esa convocatoria.
2. La **definición** y las opciones de una versión aprobada son inmutables. La retirada es un **cambio separado de estado operativo**, auditable, sin modificar `definition`. Especificar control transaccional/trigger durante la implementación; no usar la excepción genérica `approved → retired` para permitir alterar contenido.
3. Al aprobar una versión nueva: `draft → approved`; `effective_from` determina el comienzo. Puede haber versiones aprobadas futuras. La activa es la elegible con mayor fecha de efecto no futura y sujeta a una política explícita de retiro. La publicación es exclusiva/serializada por convocatoria para evitar carreras.
4. Candidaturas ya presentadas conservan el ID de versión y **sus respuestas declaradas**. Una rectificación se tramita con trazabilidad y límites de retención; no se reescribe silenciosamente el pasado.
5. Candidaturas previas: versión `legacy` identificada por convocatoria **solo si existe un plan de backfill aprobado**, sin inventar respuestas. La implementación y su migración se negocian con la propietaria del backend; KAN-107 no genera archivos de Alembic.
6. Integridad: además de la FK a `form_version.id`, validar que `form_version.call_id = application.call_id`, idealmente reforzado con integridad compuesta. Rechazar versiones de otra convocatoria, retiradas o no publicadas con 409/422 y tests negativos.
7. **Cambio de versión mientras se rellena (PO 19/11, diseño):** enviar `form_version_id`; el servidor compara con la versión vigente:
   - **Misma versión** → se acepta.
   - **Versión nueva compatible** (solo campos/opciones opcionales, sin alterar significado o requeridos) dentro de **24 h desde `effective_from` de la versión nueva** (instante de activación, no de aprobación ni de publicación; reloj del servidor, UTC) → aceptar la anterior y conservar su ID. Si `effective_from` es futuro, la ventana **no ha empezado**: la versión nueva aún no es vigente y la anterior sigue siendo la misma versión vigente. Límite: se acepta hasta `effective_from + 24 h` inclusive; después, `409`. Si se aprueba con efecto inmediato, `effective_from = approved_at`. No ampliar el plazo silenciosamente.
   - **En cualquier otro caso** (cambio incompatible, ventana vencida, versión retirada) → `409 form_version_changed` con la definición nueva. La persona **revisa y confirma** la nueva versión; se conservan en el cliente las respuestas de campos con el mismo `field.id`. Nunca se reasignan respuestas a otra versión en silencio.

### 3.1 Requisito de edad versionado — diseño aceptado PO 18/11, no implementado

Guardar años, operador, fecha de inicio del curso y `human_review`. PO 19/11: bootcamp mayoría de edad (`gte` 18); B `gte` 16. No asumir umbral global. La interpretación de la demo no sustituye validar condiciones reales con la Fundación.

El año de nacimiento es aproximado para cualquiera de los umbrales. No aceptar ni excluir automáticamente: una persona revisa con información suficiente y proporcionada. No añadir fecha completa o documentación por defecto. El requisito aplicado se conserva con la versión; cambiar umbral, operador o fecha de referencia es **incompatible** con la ventana de gracia, y obliga a revisar/confirmar una nueva versión sin reinterpretar candidaturas previas.

## 4. Ejemplo sintético

```json
{
  "form_version": 2,
  "call_id": "CALL-IA-2027-1",
  "age_requirement": {"years": 18, "operator": "gte", "reference_date": "2027-01-11", "verification": "human_review"},
  "fields": [
    {"id": "residence_region", "type": "select", "required": true, "source": "catalog:es_provinces"},
    {"id": "programming_experience", "type": "text", "required": true, "max_length": 1500},
    {
      "id": "current_situation", "type": "multi_select", "required": true, "min_selected": 1,
      "sensitivity": "special_category_candidate",
      "options": [
        {"id": "single_parent",         "label": {"es": "Cabeza de familia monoparental"}},
        {"id": "long_term_unemployed",  "label": {"es": "Desempleada/o de larga duración"}},
        {"id": "short_term_unemployed", "label": {"es": "Desempleada/o (inferior a 3 meses)"}, "excludes": ["long_term_unemployed"]},
        {"id": "disability",            "label": {"es": "Discapacidad"}, "sensitivity": "health_data_candidate"},
        {"id": "none",                  "label": {"es": "No me identifico con ninguna"}, "exclusive": true}
      ]
    },
    {"id": "referral_source", "type": "multi_select", "required": true, "options": [{"id": "friends", "label": {"es": "Amig@s o conocid@s"}}]},
    {"id": "disponibilidad", "type": "select", "required": false, "options": [{"id": "manana","label":{"es":"Mañana"}},{"id":"tarde","label":{"es":"Tarde"}},{"id":"flexible","label":{"es":"Flexible"}}]}
  ]
}
```

Ejemplo ficticio de una convocatoria que propone ≥18 a fecha de inicio; no representa el requisito de B ni una política aprobada. Campos/opciones se seleccionan por versión; no copiar la lista de A a B/C automáticamente.

Respuesta almacenada (candidatura sintética):

```json
{"form_version_id": "…", "answers": {"residence_region": "28", "programming_experience": "Texto ficticio.", "current_situation": ["long_term_unemployed"], "referral_source": ["friends"]}}
```

Si en la versión 3 se renombra la etiqueta "Cabeza de familia monoparental", la respuesta sigue siendo `single_parent` y su etiqueta histórica se resuelve con la versión 2.

## 5. Qué va en columnas y qué en `answers`

- **Columnas en `person`**: datos personales **vigentes** (`first_name`, `last_name`, `phone`, `birth_year`, `birth_country`, `nationality`, `gender`), no necesariamente inmutables.
- **`application.answers`**: lo declarado por la persona en esa convocatoria (`residence_region`, `programming_experience`, `current_situation`, `referral_source`, `disponibilidad`; si PO aprueba B/C, `computer_access`, `disability_certificate_status`, `referring_entity`) y, si es necesario para justificar la revisión, una **instantánea mínima y protegida** de los atributos actuales de `Person` que se tuvieron en cuenta. No duplicar por inercia todo el expediente.
- Los campos sensibles no están en `Summary` ni en listados (Entregable 4).
- La definición **pública** de formulario no incorpora cuotas, prioridades, listas internas de evaluación ni `review_hints` del equipo. Esos criterios requieren validación formal separada y solo podrían residir en una política de revisión **interna y autorizada**, nunca en `GET /calls/{id}/form` público. En el MVP no se implementan cuotas o prioridades no verificadas.

## 6. Consecuencias sobre contratos

| Contrato | Cambio |
|---|---|
| `GET /calls/{id}/form` (propuesto, **público**, solo lectura) | Devuelve únicamente campos y reglas de validación **visibles al solicitante** para la versión de candidatura vigente; nunca criterios internos ni permisos de personal |
| `POST /applications` | El servidor resuelve versión publicada por `call_id`; si recibe identificador de versión iniciada, verifica **mismo `call_id`, vigencia y compatibilidad**; valida contra la definición aprobada (`required`, ID válidos, exclusiones) y solo devuelve errores de campo seguros |
| `GET /applications/{id}` | Añade versión/respuestas filtradas por rol y ámbito. G3/G6 siguen política PO 19/11 del Anexo 6; listas nunca los exponen; lectura auditada |
| Gestión de versiones de formulario | **Fuera del MVP de KAN-107**: publicación inicial por configuración sintética aprobada del equipo; futuro endpoint administrativo sujeto a control y auditoría. **Los permisos de personal son independientes de las versiones de formulario y pueden cambiar durante una convocatoria.** |
| Cliente TS | `pnpm gen:api` regenera tipos; el formulario React se pinta desde `definition` (campos `text/select/multi_select`) |

## 7. Riesgos y límites

| Riesgo | Mitigación |
|---|---|
| JSON sin esquema → definiciones erróneas | Validar `definition` con un modelo Pydantic al aprobar |
| Confianza en datos del cliente | El servidor valida siempre; **trim antes de comprobar longitud**, rechazo de solo espacios; casos límite de KAN-124/#22. El frontend solo guía |
| Estadísticas sobre JSONB | Agregados por convocatoria con supresión (ya existe `min_group_size`); materializar columnas solo si se demuestra necesidad |
| Versión inexistente / cerrada | 409/422 y mensaje claro (patrón ya usado en `create_application`) |

**Casos de aceptación de la ventana de gracia (diseño; los implementa KAN-42).** Versión compatible v2 aprobada el día D con `effective_from` = D+3 a las 10:00 UTC; formulario abierto con v1:
1. Envío en D+1 → v1 es la vigente: se acepta como misma versión.
2. Envío en D+3 a las 10:00 UTC + 23 h 59 min → v2 vigente, v1 dentro de la ventana: se acepta v1 y se conserva su ID.
3. Envío exactamente en `effective_from + 24 h` → se acepta (límite inclusivo).
4. Envío en `effective_from + 24 h + 1 s` → `409 form_version_changed` con la definición de v2.
5. Si v2 es incompatible, cualquier envío tras `effective_from` → `409`, sin ventana.
6. Si v2 se aprueba con efecto inmediato, la ventana cuenta desde `approved_at`.

## 8. Gestión de permisos dinámicos independiente de las versiones

**Diseño acordado para revisión:** actualizar concesiones de lectura G3/G6 durante una convocatoria **no** cambia `form_version`, `answers`, ni la definición publicada. Se usa el permiso RBAC vigente (`role_assignment`) más la autorización granular y temporal indicada en [Entregable 6](kan-107-6-control-acceso-dinamico.md).

- **El esquema es propuesta, no implementación:** el sistema actual no tiene endpoints ni UI para conceder/revocar permisos por categoría. No afirmar que ya funciona.
- **Concesiones a otros perfiles:** aprobación funcional y ejecución por administración autorizada (`data_access.manage`), sin auto-concesión. Administración/selección tienen lectura por defecto dentro de su ámbito según PO 19/11; gestionar accesos no permite saltarse el ámbito.
- La API aplica el cambio desde el siguiente acceso, incluso si el frontend conserva una sesión; no basta ocultar componentes React.
- El acceso y la revocación quedan auditados sin valores de campos; la Fundación deberá definir quién tiene autoridad para aprobar los accesos a datos reales.

**EN:** Admin and selection have default access within their authorised scope. Other profiles need the base permission plus an active user/call/group grant managed by admin and audited. Detail only, never lists or logs. PO decision of 19 November; not implemented. Grant changes never alter versions or historic answers.

## 9. Norma obligatoria de integración de esquema

**KAN-107 ES SOLO DISEÑO Y NO DEBE GENERAR, COMMITAR NI NUMERAR MIGRACIONES.** La única persona propietaria de la cadena Alembic del módulo de admisión es backend (Elizabeth) bajo el alcance de KAN-42 y coordinación con David y el equipo. Si el cambio entra en un trabajo de admisión ya abierto y no integrado, se agrega allí con revisión; si ya está fusionado, se crea una revisión **únicamente en la fase de implementación**, partiendo de `alembic heads` y `down_revision` reales. **No reservar IDs, ni crear una rama independiente con su propio HEAD.** Ver Entregable 4.

## English edition (equivalent sections, KAN-107 V2)

**Decision.** One new table `form_version` stores an immutable, approved JSON definition per call (option C). Applications keep `form_version_id` and store answers as stable option IDs. Alternatives rejected: YAML in the repo (no FK, needs a deploy per change) and a fully relational field/option model (over-engineering).

**§1 Requirements.** Immutable identifiable versions per call and stable IDs; applications retain their version and answers. PO 19 November: B concrete date → application, organise/notify → contact. C outside MVP.

**§3.1 Age (PO 19 November, not implemented).** Age at course start; bootcamp adulthood (`gte` 18), B at least 16 (`gte` 16). Birth year alone goes to human review. Changing age requirements is incompatible with the grace rule; no automatic exclusion or reinterpretation of old answers.

**§3 Rules.** The backend resolves the published, effective version for the same `call_id`. Approved definitions are immutable; retirement is a separate, audited state. Submitted applications keep their version and declared answers. Legacy versions only with an approved backfill plan. The API validates that version and application belong to the same call.

**Rule 7 — version changes while filling (PO 19 November).** Same version accepted; a compatible prior version accepted until `effective_from + 24 h` of the new version (activation instant, not approval or publication; server clock, UTC; inclusive boundary). While `effective_from` is in the future the window has not started and the prior version is still the effective one. Immediate approval sets `effective_from = approved_at`; otherwise `409 form_version_changed` and user review/reconfirmation. No silent remapping.

**§6–§7.** Contract consequences (public read-only `GET /calls/{id}/form`, server-side validation on `POST /applications`, group-filtered `GET /applications/{id}`) and risks (schema-less JSON, client trust, JSONB statistics). Trim before length checks and reject whitespace-only text (KAN-124/#22). B/C fields and option sets must be approved per version, with certificate status and referring entity protected as G6.

**§8 Dynamic permissions.** Admin and selection have default access within their authorised scope. Other profiles need the base permission plus an active user/call/group grant managed by admin and audited. Detail only, never lists or logs. PO decision of 19 November; not implemented. For additional grants a functional owner approves and an authorised administrator executes; no self-grant. Effective next request, audited without values, independent of form versions.

**§9 Schema integration.** KAN-107 is design-only and must not create, number or reserve Alembic migrations; backend owns the single chain under KAN-42.
