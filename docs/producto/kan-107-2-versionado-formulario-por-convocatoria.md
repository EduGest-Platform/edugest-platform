# KAN-107 · Entregable 2 — Versionado del formulario por convocatoria / Per-call form versioning

**Estado:** revisión documental V2 para aprobación PO/Anas. Ningún modelo, migración ni contrato modificado. **Regla: Claude NO debe crear migraciones ni reservar números de revisión**; coordinación por el backend owner en KAN-42.
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

**Evidencia de alcance:** el formulario **de inscripción** del bootcamp contiene 14 campos (inventario de Anas). El curso de 15 h usa un **formulario de contacto**, no una candidatura: un futuro flujo `Lead/ContactRequest` debe permanecer separado y **no** crea `Application`. El versionado de este documento se limita a formularios de **candidatura**.

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

## 4. Ejemplo sintético

```json
{
  "form_version": 2,
  "call_id": "CALL-IA-2027-1",
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
    {"id": "referral_source", "type": "multi_select", "required": false, "options": [{"id": "friends", "label": {"es": "Amig@s o conocid@s"}}]},
    {"id": "disponibilidad", "type": "select", "required": false, "options": [{"id": "manana","label":{"es":"Mañana"}},{"id":"tarde","label":{"es":"Tarde"}},{"id":"flexible","label":{"es":"Flexible"}}]}
  ]
}
```

Respuesta almacenada (candidatura sintética):

```json
{"form_version_id": "…", "answers": {"residence_region": "28", "programming_experience": "Texto ficticio.", "current_situation": ["long_term_unemployed"], "referral_source": ["friends"]}}
```

Si en la versión 3 se renombra la etiqueta "Cabeza de familia monoparental", la respuesta sigue siendo `single_parent` y su etiqueta histórica se resuelve con la versión 2.

## 5. Qué va en columnas y qué en `answers`

- **Columnas en `person`**: datos personales **vigentes** (`first_name`, `last_name`, `phone`, `birth_year`, `birth_country`, `nationality`, `gender`), no necesariamente inmutables.
- **`application.answers`**: lo declarado por la persona en esa convocatoria (`residence_region`, `programming_experience`, `current_situation`, `referral_source`, `disponibilidad`) y, si es necesario para justificar la revisión, una **instantánea mínima y protegida** de los atributos actuales de `Person` que se tuvieron en cuenta. No duplicar por inercia todo el expediente.
- Los campos sensibles no están en `Summary` ni en listados (Entregable 4).
- La definición **pública** de formulario no incorpora cuotas, prioridades, listas internas de evaluación ni `review_hints` del equipo. Esos criterios requieren validación formal separada y solo podrían residir en una política de revisión **interna y autorizada**, nunca en `GET /calls/{id}/form` público. En el MVP no se implementan cuotas o prioridades no verificadas.

## 6. Consecuencias sobre contratos

| Contrato | Cambio |
|---|---|
| `GET /calls/{id}/form` (propuesto, **público**, solo lectura) | Devuelve únicamente campos y reglas de validación **visibles al solicitante** para la versión de candidatura vigente; nunca criterios internos ni permisos de personal |
| `POST /applications` | El servidor resuelve versión publicada por `call_id`; si recibe identificador de versión iniciada, verifica **mismo `call_id`, vigencia y compatibilidad**; valida contra la definición aprobada (`required`, ID válidos, exclusiones) y solo devuelve errores de campo seguros |
| `GET /applications/{id}` | Añade `form_version` y **respuestas filtradas por grupo**: requiere `applications.read` en su ámbito y, para G3/G6, concesión de grupo activa para esa `call_id`. Los listados nunca exponen esos datos. Lecturas protegidas se auditan |
| Gestión de versiones de formulario | **Fuera del MVP de KAN-107**: publicación inicial por configuración sintética aprobada del equipo; futuro endpoint administrativo sujeto a control y auditoría. **Los permisos de personal son independientes de las versiones de formulario y pueden cambiar durante una convocatoria.** |
| Cliente TS | `pnpm gen:api` regenera tipos; el formulario React se pinta desde `definition` (campos `text/select/multi_select`) |

## 7. Riesgos y límites

| Riesgo | Mitigación |
|---|---|
| JSON sin esquema → definiciones erróneas | Validar `definition` con un modelo Pydantic al aprobar |
| Confianza en datos del cliente | El servidor valida siempre; el frontend solo guía |
| Estadísticas sobre JSONB | Agregados por convocatoria con supresión (ya existe `min_group_size`); materializar columnas solo si se demuestra necesidad |
| Versión inexistente / cerrada | 409/422 y mensaje claro (patrón ya usado en `create_application`) |

## 8. Gestión de permisos dinámicos independiente de las versiones

**Diseño acordado para revisión:** actualizar concesiones de lectura G3/G6 durante una convocatoria **no** cambia `form_version`, `answers`, ni la definición publicada. Se usa el permiso RBAC vigente (`role_assignment`) más la autorización granular y temporal indicada en [Entregable 6](kan-107-6-control-acceso-dinamico.md).

- **El esquema es propuesta, no implementación:** el sistema actual no tiene endpoints ni UI para conceder/revocar permisos por categoría. No afirmar que ya funciona.
- Admin autorizado aprueba/ejecuta una concesión por usuario, ámbito de convocatoria, grupo de campos, finalidad y periodo; no se permite auto-concesión.
- La API aplica el cambio desde el siguiente acceso, incluso si el frontend conserva una sesión; no basta ocultar componentes React.
- El acceso y la revocación quedan auditados sin valores de campos; la Fundación deberá definir quién tiene autoridad para aprobar los accesos a datos reales.

**EN:** Access grants are operational, per-user/per-call and time-bound. They can change during an active call without changing a form definition or historic answers. The API enforces both role/scope and field-group grants; admin UI and persistence are not yet built.

## 9. Norma obligatoria de integración de esquema

**KAN-107 ES SOLO DISEÑO Y NO DEBE GENERAR, COMMITAR NI NUMERAR MIGRACIONES.** La única persona propietaria de la cadena Alembic del módulo de admisión es backend (Elizabeth) bajo el alcance de KAN-42 y coordinación con David y el equipo. Si el cambio entra en un trabajo de admisión ya abierto y no integrado, se agrega allí con revisión; si ya está fusionado, se crea una revisión **únicamente en la fase de implementación**, partiendo de `alembic heads` y `down_revision` reales. **No reservar IDs, ni crear una rama independiente con su propio HEAD.** Ver Entregable 4.
