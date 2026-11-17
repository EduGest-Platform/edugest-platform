# KAN-107 · Entregable 1 — Diccionario de datos consolidado / Consolidated data dictionary

**Estado:** borrador para revisión (no es validación jurídica) · **Fecha:** 17/11/2026 · **Rama:** `docs/KAN-107-data-governance`
**Base reutilizada:** [`docs/producto/diccionario-campos-candidatura.md`](https://github.com/EduGest-Platform/edugest-platform/pull/15) (Anas, KAN-92/93). Está **solo en la rama del PR #15** (`feat/KAN-115-api-errors-401-403`, abierto); **no está en `dev`**. Este documento *no copia* ese inventario: lo referencia por número de fila (`#1`…`#14`) y le añade gobierno, destino técnico y trazabilidad.

> **EN summary:** Technical + functional dictionary for the 14 fields of the real Somos F5 form plus EduGest-only fields. Each field has an owner entity (Person vs Application), a stable technical id, a proposed legal-basis *candidate* (all pending confirmation by the Foundation/DPO), access scope and status. Nothing here changes code, models or contract yet.

## 0. Cómo leer este documento

- **Confirmado** = decisión funcional comunicada por la PO el 17/11/2026 (no es validación jurídica).
- **Propuesta** = recomendación de este análisis, pendiente de aprobación.
- **Pendiente** = depende de Melissa / Fundación / DPO; no se inventa.
- Estado del campo: **MVP**, **POSTERIOR**, **PENDIENTE** (necesidad por validar).
- Todos los datos son **sintéticos**; los dominios de correo y teléfonos serán ficticios.

### Decisiones de la PO ya incorporadas (17/11/2026, funcionales)

| Decisión | Efecto en este diccionario |
|---|---|
| Mantener nacionalidad, país de nacimiento y género | Campos `#6`, `#7`, `#8` permanecen en el diseño. Se documenta el riesgo y la alternativa en el Entregable 3; **no se eliminan**. |
| Opciones de "situación actual" configurables por convocatoria | Campo `#11` y `#12` pasan a ser *campos configurables* con opciones de ID estable (Entregable 2). |
| Disponibilidad no obligatoria en la inscripción inicial | `disponibilidad` pasa a opcional (cambio **incompatible** en API y BD, ver §4). |
| Separar nombre y apellidos | `#1` y `#2` → `first_name`, `last_name`. Cambio incompatible (ver §4). |

### Respuestas del equipo (17/11/2026) a las preguntas para Melissa

Dadas por el equipo, **no por Melissa**; quedan como supuestos de trabajo a ratificar por la Fundación.

| Tema | Respuesta |
|---|---|
| Nacionalidad, país de nacimiento, género | El financiador los exige (figura en la web de Somos F5). Se piden como en el formulario real |
| Uso | No se usa nacionalidad para admitir o no. Género y vulnerabilidad pueden pesar en la revisión (p. ej. 70–80 % de mujeres en una convocatoria; prioridad por nacionalidad extranjera unida a otras vulnerabilidades). Siempre decide una persona |
| Situación actual por convocatoria | En el MVP se **simula** con datos sintéticos de seed; la Fundación no la va a implementar ahora (prueba de concepto) |
| "Joven <30" | Autodeclaración si el formulario no pide fecha de nacimiento |
| Experiencia vs. motivación | Se mantiene la experiencia en programación |
| "Cómo nos has conocido" | Opcional, con "otros". Pendiente de revisar con la captura del formulario real |
| Edad mínima | 18 años |
| Residencia | Depende de la convocatoria (Madrid, Barcelona, online). Se pide siempre; lo confirma una persona |
| Quién ve los datos | Selección, preselección y administración (todo el personal que gestiona candidaturas). No coder, alumno ni aspirante |
| Rectificación/borrado | Llegan por correo. Proceso **pendiente** (fuera del alcance de la prueba de concepto) |
| Responsable del tratamiento y DPO | **Pendiente**; se deja anotado en el README, no se resuelve ahora |
| Revisión legal (RGPD/LOPDGDD/AEPD) | **Fuera del alcance** del proyecto (gratuito, datos sintéticos); corresponde a la Fundación en una fase posterior |

### Evidencia adicional: formulario del curso de 15 h (captura del equipo, 17/11/2026)

Fuente: captura de `landings.somosf5.org/proyecto-ai4inclusion-curso15h` aportada por el equipo (PDF y capturas; el PDF no se pudo procesar en esta sesión, se usó la imagen, de baja resolución: **confirmar los textos exactos**).

| Aspecto | Formulario bootcamp (inventario de Anas) | Formulario curso 15 h (captura) |
|---|---|---|
| Encabezado | Inscripción | "¿Quieres saber más? Déjanos tus datos para ponernos en contacto contigo" (solicitud de contacto) |
| Campos visibles | 14 campos (§2.1) | Nombre\*, Apellidos\*, Correo\*, **Ciudad\*** (texto), Teléfono, comentarios, "acepto comunicaciones", "acepto tratamiento de datos"\*, reCAPTCHA |
| Nacionalidad, país de nacimiento, género, situación, año de nacimiento | Sí | **No aparecen** |

Consecuencias:
1. **Cada oferta formativa tiene su propio formulario**, con campos distintos: refuerza el versionado por convocatoria (Entregable 2). La respuesta del equipo sobre "el financiador exige nacionalidad, país y género" se refiere al formulario de **bootcamp**; no debe extenderse a otros cursos.
2. Aparece un campo **`city`** (texto libre, "Ciudad") que el inventario no tenía. En el bootcamp la residencia es un desplegable de provincia/distrito (#9). Propuesta: ambos son configurables por versión (`residence_region` select o `city` texto).
3. Hay que **confirmar con Anas/PO qué formulario es la referencia del MVP** (bootcamp de 1250 h o curso de 15 h). El diccionario documenta el bootcamp, que es el más completo; el del curso de 15 h cabe como una segunda definición con menos campos.
4. En el curso de 15 h "teléfono" y los comentarios no parecen obligatorios (confirmar).

## 1. Auditoría del inventario (qué falta, qué se duplica, qué choca)

### 1.1 Estado real en `dev` (evidencia)

| Elemento | Dónde | Hoy |
|---|---|---|
| `ApplicationCreate`: `call_id, nombre, email, motivacion, disponibilidad, acepta_datos_sinteticos` | `api/app/modules/admissions/schemas.py` | 6 campos |
| `Person`: `display_name, email, legacy_ref, is_synthetic, created_at` | `api/app/modules/identity/models.py` | 1 solo nombre |
| `Application`: `codigo, legacy_ref, person_id, call_id, stage, motivacion, disponibilidad (NOT NULL), acepta_datos_sinteticos` | `api/app/modules/admissions/models.py` | sin versión de formulario |
| `Call`: `id, program_id, nombre, codigo_prefix, opens_on, closes_on, plazas, estado, next_seq` | `api/app/modules/catalog/models.py` | sin configuración de formulario |
| Contrato | `contracts/openapi.json` (`ApplicationCreate`, `ApplicationDetail`…) | refleja lo anterior |
| Logging | `api/app` | no hay `logging` propio; `audit_event.meta` documenta "IDs y códigos, nunca datos personales" |

### 1.2 Hallazgos

| ID | Tipo | Hallazgo | Acción propuesta |
|---|---|---|---|
| H1 | Ausente | 11 de los 14 campos del formulario real **no existen** en BD/API (`#2, #4–#12`, y `#13`). | Añadir según §2 (migración incremental, Entregable 4). |
| H2 | Duplicidad | `#5 Año de nacimiento` ↔ opción "Joven de menos de 30 años" de `#11`. | Derivar la condición de `birth_year`; mantener la opción solo si el financiador exige autodeclaración (Pendiente). |
| H3 | Duplicidad | `#6/#7` ↔ opción "Inmigrante" de `#11`. | Documentar que son datos distintos (hecho vs autodeclaración de situación); decidir con PO si ambos son necesarios (minimización). |
| H4 | Duplicidad | "Desempleada/o (<3 meses)" y "de larga duración" son excluyentes entre sí. | Regla de validación por convocatoria (§3.3), no por UI. |
| H5 | Regla | "No me identifico con ninguna…" es excluyente con el resto de `#11`. | Opción con `exclusive: true` en la definición del formulario. |
| H6 | Persona vs candidatura | Residencia (`#9`), experiencia (`#10`), situación (`#11`), canal (`#12`) cambian con el tiempo/convocatoria. | Van a **Application** (instantánea de lo declarado en esa candidatura). |
| H7 | Persona vs candidatura | Nombre, apellidos, correo, teléfono, año de nacimiento, país de nacimiento, nacionalidad, género son estables. | Van a **Person** (un expediente por persona, ADR-0002). Ver H8. |
| H8 | Riesgo de integridad | `create_application` **reutiliza** la `Person` por correo y **no actualiza** sus datos. Un segundo envío con otro teléfono se perdería o, si se actualizara, alteraría el pasado. | Regla propuesta: Person guarda el dato vigente; **cada Application congela sus respuestas** en `answers`. Actualizar Person solo por acción explícita y auditada. |
| H9 | Incompatibilidad | `disponibilidad`: BD `NOT NULL`, API `Literal["Mañana","Tarde","Flexible"]` obligatorio; la PO la quiere opcional. | `nullable` en BD + `\| None = None` en Pydantic + regenerar cliente TS. |
| H10 | Incompatibilidad | `nombre` (min 2) ↔ `display_name` (120). Hay que separar. | Añadir `first_name`/`last_name`; mantener `display_name` como campo **derivado** durante la transición. |
| H11 | Pendiente | `motivacion` **no existe en el formulario real** (el real pide experiencia, `#10`). | Marcar PENDIENTE: no pedir dos textos largos sin justificar necesidad (minimización). Decide la PO. |
| H12 | Técnico | `acepta_datos_sinteticos` es un aviso de entorno de demo, no un consentimiento RGPD. | Mantener solo mientras haya datos sintéticos; **no** reutilizarlo como base jurídica ni como `#14`. |
| H13 | Pendiente | `#13` (comunicaciones) y `#14` (tratamiento): el real los mezcla en el mismo bloque. | Separar finalidades; `#13` fuera de MVP (la demo no envía comunicaciones). |
| H14 | Exposición | `PersonOut`/`ApplicationSummary` (listados) llegan a todo el que tenga `applications.read`. | Los nuevos datos sensibles **no** entran en listados ni en `Summary`; solo en detalle y con el mismo permiso `applications.read` (decisión del equipo 17/11: no hace falta permiso nuevo en el MVP). |
| H15 | Consistencia | El prototipo web (`src/gistar/views/Aspirant.tsx`, `seed.json`) usa `nombre_ficticio`, `motivacion`, `disponibilidad`. | Migrar al cliente generado (`src/shared/api/schema.gen.ts`) en el paso de frontend. |

## 2. Diccionario por campo

Convenciones: **Entidad** = `P` Person · `A` Application (instantánea) · `C` Call/FormVersion. Los nombres técnicos son **propuestos**; los IDs de opción son estables y nunca se reutilizan.
**Cat.** = categoría RGPD *propuesta* tras análisis preliminar (no definitiva): `ORD` dato ordinario · `ORD*` ordinario con riesgo de proxy/discriminación (evaluar) · `ESP?` posible categoría especial art. 9 (evaluar caso a caso) · `TEC` técnico/operativo.
**Base jurídica** = *candidata*, **pendiente de confirmar por la Fundación/DPO**; no se afirma ninguna.

### 2.1 Campos del formulario real (14)

| # | Funcional | Técnico (API / BD) | Tipo y formato | Obligatorio (propuesta) y validación | Origen | Entidad | Cat. | Estado |
|---|---|---|---|---|---|---|---|---|
| 1 | Nombre | `first_name` / `person.first_name` | `str` 1–80, trim, sin solo espacios | Sí. `min_length=1` (hay nombres de 1 letra) | Persona (formulario) | P | ORD | MVP |
| 2 | Apellidos | `last_name` / `person.last_name` | `str` 1–120 | Sí (real: obligatorio) | Persona | P | ORD | MVP |
| 3 | Correo | `email` / `person.email` | email, normalizado, único | Sí. Ya existe (`normalize_email`). Demo: solo `@example.test` | Persona | P | ORD | MVP (existe) |
| 4 | Teléfono | `phone` / `person.phone` | E.164 (`+34600000000`) `str` ≤16 | Sí (real) — necesario para AS-IS (recordatorios) | Persona | P | ORD | MVP |
| 5 | Año de nacimiento | `birth_year` / `person.birth_year` | `int`; `birth_year <= año actual − 18` (edad mínima 18, dato del equipo 17/11) | Sí (real). Solo año (minimización). Con solo el año no se prueba la mayoría de edad exacta: lo comprueba la persona que revisa | Persona | P | ORD | MVP |
| 6 | País de nacimiento | `birth_country` / `person.birth_country` | ISO 3166-1 alfa-2 `str(2)` | **Sí** (el equipo indica que el financiador lo exige y figura en la web de Somos F5) | Persona | P | ORD* | MVP (uso restringido, ver G3) |
| 7 | Nacionalidad | `nationality` / `person.nationality` | ISO 3166-1 alfa-2 `str(2)` | **Sí** (ídem #6) | Persona | P | ORD* | MVP (uso restringido, ver G3) |
| 8 | Género | `gender` / `person.gender` | opciones estables: `woman, man, non_binary, other, prefer_not_to_say` | **Sí** (ídem #6). Se mantiene `prefer_not_to_say` como opción válida. Uso: cuotas/estadística de la convocatoria (ver G3) | Persona (autodeclarado) | P | ORD* | MVP (uso restringido, ver G3) |
| 9 | Provincia/distrito de residencia | `residence_region` / `application.answers` | código de provincia (INE) o distrito (PT) | Sí. El requisito de residencia **depende de la convocatoria** (Madrid, Barcelona, online = sin requisito); lo confirma una persona al revisar, no hay exclusión automática | Persona | A | ORD | MVP |
| 10 | Experiencia en programación | `programming_experience` / `application.answers` | texto 1–1500 | Sí (real). No pedir datos sensibles (aviso en UI) | Persona | A | ORD | MVP |
| 11 | Situación actual (varias) | `current_situation` / `application.answers` | lista de IDs de opción de la versión de formulario | Sí, ≥1. `none` excluyente (H5). Opciones por convocatoria (PO) | Persona (autodeclarado) | A | **ESP?** (p. ej. discapacidad) / ORD* | MVP con cuidado |
| 12 | ¿Cómo nos conociste? (varias) | `referral_source` / `application.answers` | lista de IDs | **Opcional**, con opción `other` (decisión del equipo 17/11; pendiente de contrastar con la captura del formulario real) | Persona | A | ORD | MVP |
| 13 | Comunicaciones de Somos F5 | `marketing_opt_in` | `bool` | No | Persona | P (con fecha y versión de texto) | ORD | POSTERIOR |
| 14 | Información/consentimiento de tratamiento | `privacy_notice_version`, `privacy_notice_ack_at` / `application` | `str` + `datetime` | Sí. **Es acuse de información (art. 13), no se presume base jurídica** (H12) | Persona | A | TEC | MVP |

### 2.2 Campos propios de EduGest

| Funcional | Técnico | Tipo | Obligatorio | Entidad | Cat. | Estado / nota |
|---|---|---|---|---|---|---|
| Convocatoria | `call_id` (existe) | `str(30)` FK | Sí | A | TEC | MVP (existe) |
| Versión del formulario aplicada | `form_version_id` (nuevo) | FK `form_version.id` | Sí en altas nuevas | A | TEC | MVP (Entregable 2) |
| Disponibilidad | `disponibilidad` (existe) | `Mañana\|Tarde\|Flexible` | **No** (PO 17/11) | A | ORD | MVP (cambio incompatible H9) |
| Motivación | `motivacion` (existe) | texto 10–2000 | **Opcional / heredado**: el equipo mantiene `programming_experience` (#10) como pregunta del formulario; `motivacion` no se amplía ni se exige (interpretación pendiente de confirmar) | A | ORD | Sin cambios hasta confirmar |
| Aviso de datos sintéticos | `acepta_datos_sinteticos` (existe) | `Literal[True]` | Sí mientras haya demo | A | TEC | Retirar en producción real |
| Código de candidatura | `codigo` (existe) | `str(20)` único | Auto | A | TEC | MVP (existe) |
| Etapa | `stage` (existe) | enum de 9 valores | Auto | A | TEC | Existe; las decisiones de admisión son **humanas** |
| Referencia legado | `legacy_ref` (existe) | `str(20)` | Auto | P/A | TEC | Solo datos semilla |
| Marca sintética | `is_synthetic` (existe) | `bool` | Auto | P | TEC | Existe |
| Eventos CRM | `application_event.resumen` (existe) | `str(500)` | — | A | ORD | Ya avisa: "No incluir datos de salud…". Ver R6 |

### 2.3 Gobierno por campo (resumen agrupado)

Agrupado por perfil de riesgo para no repetir 24 filas idénticas; cada campo hereda la fila de su grupo.

| Grupo | Campos | Responsable funcional (propuesto) | Base jurídica *candidata* (pendiente) | Necesidad y proporcionalidad | Acceso (rol · ámbito) | Preselección / estadística / decisión humana |
|---|---|---|---|---|---|---|
| G1 Identificación y contacto | `#1–#4`, `email` | Captación (PO decide) | Art. 6.1 (b ó f ó e según naturaleza de la Fundación) — **confirmar** | Necesario para contactar y gestionar la candidatura | `applications.read`: admin global · captación programa · selección convocatoria. Coordinación y docente: **no** | Contacto; no entra en estadísticas nominales |
| G2 Edad | `#5` | Selección | Ídem G1 | Año, no fecha completa; sirve a criterio "<30" del financiador | Igual G1 | Preselección **informativa**; estadística agregada |
| G3 Origen y género | `#6, #7, #8` | PO / Fundación | **Sin confirmar** (queda para la Fundación/DPO) | Exigido por el financiador (dato del equipo, figura en la web de Somos F5) | Solo en detalle, mismo ámbito que `applications.read` (selección, preselección/captación, administración); **nunca** en listados; fuera de coder, alumno y aspirante | **Sí influye en la selección de forma documentada, siempre con revisión humana**: p. ej. cuota de mujeres de la convocatoria o prioridad por vulnerabilidad combinada con nacionalidad. **Nunca** como criterio único ni automático. Estadísticas agregadas con supresión |
| G4 Residencia | `#9` | Selección | Ídem G1 | Requisito de la convocatoria (Madrid) | Igual G1 | Señal para revisión humana; **sin exclusión automática** |
| G5 Perfil técnico | `#10`, `motivacion` | Selección | Ídem G1 | Valoración humana de itinerario | Igual G1 | Apoya revisión humana |
| G6 Situación personal | `#11` | PO / Fundación / DPO | **Posible art. 9**: si trata discapacidad u otra categoría especial hace falta además una excepción del art. 9.2 — **pendiente DPO** | Opciones definidas por financiador/convocatoria; justificar cada opción | Solo detalle, mismo ámbito que `applications.read`; agregados con supresión | Criterio de elegibilidad para **revisión humana**; sin decisión automatizada (art. 22) |
| G7 Captación | `#12` | Captación | Ídem G1 | Métrica de canal; no necesaria para decidir | Igual G1 | Solo estadística |
| G8 Información/consentimientos | `#13, #14` | DPO/Fundación | Texto de información art. 13; consentimiento solo donde sea base válida (p. ej. comunicaciones) | — | Registro de versión y fecha; lectura por admin | No |
| G9 Técnicos | `codigo`, `stage`, `form_version_id`, … | Equipo técnico | n/a | n/a | Según endpoint | No |

### 2.4 Retención, modificación y eliminación

| Regla | Estado | Contenido |
|---|---|---|
| Trazabilidad de acceso: toda lectura de ficha (`application.viewed`) y alta se registra en `audit_event` append-only | **Aprobada / implementada** (ADR-0003 + trigger en `0001_f1_cimientos.py`) | `meta` solo con IDs/códigos |
| Datos sintéticos: sin datos reales | **Aprobada** (CLAUDE.md, AGENTS.md) | — |
| Plazo de conservación de candidaturas **no admitidas** | **Pendiente — decide la Fundación** | Propuesta: fijar un plazo `[N meses desde cierre de la convocatoria]`; al vencer, borrado o anonimización |
| Plazo de conservación de candidaturas **admitidas** | **Pendiente** | Pasa a expediente de aprendizaje; plazo propio |
| Rectificación | **Propuesta** | La persona rectifica Person; la candidatura ya registrada conserva lo declarado, con evento de rectificación auditado |
| Supresión | **Propuesta** | Procedimiento por solicitud; `audit_event` conserva IDs sin datos personales |
| Datos de formulario sensibles | **Propuesta** | Plazo igual o menor que el general; revisión por DPO |

## 3. Entidad de destino: resumen

```
Person   (1 por persona)         Application (1 por persona+convocatoria)       Call
 first_name, last_name  ◄──────  person_id                                      id
 email, phone                    call_id ─────────────────────────────────────► id
 birth_year                      form_version_id ──► FormVersion (Entregable 2)
 birth_country, nationality      answers (JSONB): residence_region,
 gender                                  programming_experience, current_situation,
 marketing_opt_in                        referral_source, disponibilidad(opc.)
                                 privacy_notice_version / _ack_at
                                 stage, codigo, …
```

Criterio de reparto: **dato estable de la persona → Person; lo declarado para una convocatoria concreta → Application (congelado)**.

## 4. Cambios incompatibles detectados

| Cambio | Rompe | Mitigación incremental |
|---|---|---|
| `nombre` → `first_name` + `last_name` | `ApplicationCreate`, `Person.display_name`, `Aspirant.tsx`, `seed.json`, tests | Fase A: añadir columnas *nullable* y aceptar **ambos** formatos; Fase B: migrar frontend; Fase C: hacer obligatorios y retirar `nombre`. |
| `disponibilidad` opcional | BD `NOT NULL`, `Literal` obligatorio, `ApplicationDetail.disponibilidad: str` | `ALTER COLUMN DROP NOT NULL` (reversible) + tipo `str \| None`. Cambio **compatible hacia atrás** en lectura. |
| Nuevos campos obligatorios | Clientes antiguos que no los envían | Obligatorios solo para `form_version` nuevas; las candidaturas previas se rellenan con versión 0 ("legado"). |
| `answers` JSONB | Consultas SQL por campo | Campos usados en filtros/estadísticas se materializan como columna solo si se demuestra necesidad (no anticipar). |

## 5. Trazabilidad fuente → diccionario

| Fuente | Estado de acceso | Qué se usó |
|---|---|---|
| `docs/producto/diccionario-campos-candidatura.md` (PR #15) | **Leído** vía `refs/pull/15/head`; no integrado en `dev` | Filas `#1–#14`, preguntas a la PO |
| `schemas.py`, `models.py` (`admissions`, `identity`, `catalog`) | **Leído** en `dev` | §1.1 |
| `contracts/openapi.json` | **Leído** (esquemas `ApplicationCreate`, etc.) | §1.1 |
| `docs/reports/RBAC_MATRIX_2026-11-13.md` | **Leído** (no versionado aún en `dev`, estado `CODE_PRESENT_NOT_RUN`) | Accesos |
| KAN-92 / KAN-93 / KAN-107 / KAN-112 (Jira y comentarios) | **No accesible** desde esta sesión | **Bloqueo B1**: contrastar |
| AS-IS y aclaraciones de Melissa (Drive) | **No accesible** | **Bloqueo B2**: se cita lo que recoge el documento de Anas (06 y 08/11/2026) |
| Formulario real Somos F5 | **No re-consultado**; se usa la captura de Anas del 17/11/2026 | — |
