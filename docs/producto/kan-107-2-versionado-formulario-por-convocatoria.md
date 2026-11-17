# KAN-107 · Entregable 2 — Versionado del formulario por convocatoria / Per-call form versioning

**Estado:** propuesta de diseño para aprobación. No se ha modificado ningún modelo, migración ni contrato.
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

## 2. Comparativa breve

| Criterio | A. JSON/YAML versionado **en el repositorio** | B. Tablas relacionales (`form_field`, `form_option`, `form_version`…) | **C. Recomendada: 1 tabla `form_version` con definición JSON en BD** |
|---|---|---|---|
| Tablas nuevas | 0 | 3–4 | **1** |
| Coste de migración | Bajo, pero la candidatura referencia un texto de versión sin FK | Alto (varias migraciones + joins) | **Bajo-medio (1 migración)** |
| Cambiar opciones de una convocatoria | Requiere PR + despliegue | Posible sin despliegue | **Posible sin despliegue** |
| Traza de aprobación | Git (autor de PR), no vinculada a la BD | Sí, en BD | **Sí, en BD (`approved_by/at`)** |
| Integridad referencial candidatura→versión | No | Sí | **Sí (FK)** |
| Validación en API | Carga de fichero | Consultas | **Carga de una fila; validador Pydantic dinámico** |
| Riesgo de sobreingeniería | Bajo | **Alto** | Bajo |

**Recomendación única para el MVP: opción C.** Mantiene integridad (FK + inmutabilidad), da trazabilidad de aprobación y no obliga a desplegar para cambiar las opciones por convocatoria (decisión de la PO). Un cambio a tablas relacionales solo se justificaría si aparecen consultas SQL frecuentes sobre opciones, algo que hoy no existe.

## 3. Esquema conceptual

```
call 1 ──< form_version >── 1 app_user (approved_by)
              │ id (uuid)
              │ call_id        FK call.id
              │ version        int, UNIQUE(call_id, version)
              │ status         'draft' | 'approved' | 'retired'
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
1. Solo una versión `approved` con `effective_from <= now()` y la mayor `version` está **vigente** por convocatoria; las altas usan esa.
2. `approved` es **inmutable** (trigger `BEFORE UPDATE OR DELETE` que lo rechaza salvo pasar a `retired`).
3. Corregir una opción ⇒ nueva versión (v+1). Las candidaturas existentes siguen apuntando a la antigua.
4. Candidaturas previas a la feature: `form_version` v0 "legado" por convocatoria (migración de datos), sin inventar respuestas.

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

- **Columnas en `person`**: datos estables (`first_name`, `last_name`, `phone`, `birth_year`, `birth_country`, `nationality`, `gender`).
- **`application.answers`**: lo configurable o dependiente de convocatoria (`residence_region`, `programming_experience`, `current_situation`, `referral_source`, `disponibilidad`).
- Los campos sensibles no están en `Summary` ni en listados (Entregable 4).

## 6. Consecuencias sobre contratos

| Contrato | Cambio |
|---|---|
| `GET /calls/{id}/form` (nuevo, **público**, solo lectura) | Devuelve la versión vigente (sin datos personales) para que React pinte el formulario |
| `POST /applications` | `ApplicationCreate` incluye `form_version` (int, opcional → por defecto la vigente) y `answers: dict[str, Any]`; el servidor valida contra la versión (campos requeridos, IDs de opción válidos, exclusiones). Responde 422 con el ID de campo fallido |
| `GET /applications/{id}` | Añade `form_version` y `answers` solo si `applications.read_sensitive` para los campos marcados |
| `POST/PATCH` de administración de formularios | **Fuera de MVP**: la versión se carga por seed/migración con PR revisado; después endpoint con permiso `forms.manage` |
| Cliente TS | `pnpm gen:api` regenera tipos; el formulario React se pinta desde `definition` (campos `text/select/multi_select`) |

## 7. Riesgos y límites

| Riesgo | Mitigación |
|---|---|
| JSON sin esquema → definiciones erróneas | Validar `definition` con un modelo Pydantic al aprobar |
| Confianza en datos del cliente | El servidor valida siempre; el frontend solo guía |
| Estadísticas sobre JSONB | Agregados por convocatoria con supresión (ya existe `min_group_size`); materializar columnas solo si se demuestra necesidad |
| Versión inexistente / cerrada | 409/422 y mensaje claro (patrón ya usado en `create_application`) |
