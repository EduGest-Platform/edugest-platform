# KAN-107 · Entregable 1 — Diccionario de datos consolidado / Consolidated data dictionary

**Estado:** revisión documental V2 para aprobación PO/Anas (no es validación jurídica ni código implementado) · **Fecha base:** 17/11/2026 · **Ubicación de entrega:** paquete local; **rama remota no creada/verificada**. No declarar PR de KAN-107 existente.
**Base reutilizada:** [`docs/producto/diccionario-campos-candidatura.md`](https://github.com/EduGest-Platform/edugest-platform/pull/15) (Anas, KAN-92/93). Está **solo en la rama del PR #15** (`feat/KAN-115-api-errors-401-403`, abierto); **no está en `dev`**. Este documento *no copia* ese inventario: lo referencia por número de fila (`#1`…`#14`) y le añade gobierno, destino técnico y trazabilidad.

> **EN summary:** Technical + functional dictionary for the 14 fields of the real Somos F5 form plus EduGest-only fields. Each field has an owner entity (Person vs Application), a stable technical id, a proposed legal-basis *candidate* (all pending confirmation by the Foundation/DPO), access scope and status. Nothing here changes code, models or contract yet.

## 0. Cómo leer este documento

- **OBSERVADO** = campo mostrado en el formulario documentado por Anas, con fuente y fecha (no implica obligación de financiador).
- **DECISIÓN PO** = instrucción funcional comunicada en KAN-93 el 17/11/2026 (no es validación jurídica).
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
| Nacionalidad, país de nacimiento, género | **OBSERVADO:** obligatorios en el formulario del bootcamp inventariado por Anas. **DECISIÓN PO:** mantenerlos en el diseño sintético. **PENDIENTE MELISSA:** confirmar si hay exigencia contractual del financiador y para qué finalidad se utilizarían. |
| Uso | **PENDIENTE DE APROBACIÓN:** no se ha validado documentalmente ninguna cuota, prioridad ni tratamiento diferencial. El MVP muestra estos campos solo para revisión humana autorizada con datos sintéticos; **no implementa scoring ni cuotas basadas en género, nacionalidad o vulnerabilidad**. Una intervención humana no basta por sí sola para legitimar estos criterios. |
| Situación actual por convocatoria | En el MVP se **simula** con datos sintéticos de seed; la Fundación no la va a implementar ahora (prueba de concepto) |
| "Joven <30" | Autodeclaración si el formulario no pide fecha de nacimiento |
| Experiencia vs. motivación | Se mantiene la experiencia en programación |
| "Cómo nos has conocido" | Opcional, con "otros". Pendiente de revisar con la captura del formulario real |
| Edad mínima | 18 años |
| Residencia | Depende de la convocatoria (Madrid, Barcelona, online). Se pide siempre; lo confirma una persona |
| Quién ve los datos | **DECISIÓN DE PRODUCTO REFINADA:** acceso operativo según **rol + convocatoria + grupo de datos + concesión vigente**. Los roles de captación/selección pueden consultar datos operativos dentro de su ámbito; los grupos protegidos requieren habilitación específica, no acceso automático. Coordinación solo agregados; docente no gestiona admisión. La persona solicitante conserva sus derechos sobre sus propios datos: esto no significa que el personal pueda mostrárselos por defecto. |
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
1. **Son dos flujos diferentes:** el bootcamp es **inscripción/candidatura**, mientras el curso de 15 h es **contacto/lead**. Un lead **no crea `Application`** por defecto. Las diferencias pueden justificar reutilizar componentes visuales, no unificar procesos ni finalidades automáticamente.
2. El campo `city` solo está **observado en contacto/lead**; **no se incorpora a la definición de candidatura** del MVP sin requisito aprobado. `residence_region` sigue siendo un campo de inscripción.
3. **Referencia del MVP de inscripción:** formulario de **bootcamp** inventariado por Anas (KAN-92/93). El curso de 15 h queda como flujo futuro de captación/lead, sujeto a decisión y modelo propios.
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
| H2 | Posible duplicidad | `#5 Año de nacimiento` ↔ opción "Joven de menos de 30 años" de `#11`. | No derivar automáticamente criterios de elegibilidad con solo el año; conservar declaración y revisión humana, pendiente de ratificación de la Fundación. |
| H3 | Duplicidad | `#6/#7` ↔ opción "Inmigrante" de `#11`. | Documentar que son datos distintos (hecho vs autodeclaración de situación); decidir con PO si ambos son necesarios (minimización). |
| H4 | Duplicidad | "Desempleada/o (<3 meses)" y "de larga duración" son excluyentes entre sí. | Regla de validación por convocatoria (§3.3), no por UI. |
| H5 | Regla | "No me identifico con ninguna…" es excluyente con el resto de `#11`. | Opción con `exclusive: true` en la definición del formulario. |
| H6 | Persona vs candidatura | Residencia (`#9`), experiencia (`#10`), situación (`#11`), canal (`#12`) cambian con el tiempo/convocatoria. | Van a **Application** (instantánea de lo declarado en esa candidatura). |
| H7 | Persona vs candidatura | Nombre, teléfono, nacionalidad y género **pueden cambiar**. | `Person` representa el valor **actual**; la declaración necesaria para la decisión de cada convocatoria se conserva separadamente en una **instantánea protegida de `Application`**, con retención limitada. |
| H8 | Riesgo de integridad | `create_application` reutiliza `Person` por correo. El cambio futuro de datos actuales podría reinterpretar decisiones históricas. | `Person` actualizable con control; `Application.submitted_snapshot` contiene solo valores **efectivamente usados** en esa candidatura y se conserva según política de retención, con rectificaciones auditadas y minimización. No actualizar datos actuales por reenvío silencioso. |
| H9 | Incompatibilidad | `disponibilidad`: BD `NOT NULL`, API `Literal["Mañana","Tarde","Flexible"]` obligatorio; la PO la quiere opcional. | `nullable` en BD + `\| None = None` en Pydantic + regenerar cliente TS. |
| H10 | Incompatibilidad | `nombre` (min 2) ↔ `display_name` (120). Hay que separar. | Añadir `first_name`/`last_name`; mantener `display_name` como campo **derivado** durante la transición. |
| H11 | Pendiente | `motivacion` **no existe en el formulario real** (el real pide experiencia, `#10`). | Marcar PENDIENTE: no pedir dos textos largos sin justificar necesidad (minimización). Decide la PO. |
| H12 | Técnico | `acepta_datos_sinteticos` es un aviso de entorno de demo, no un consentimiento RGPD. | Mantener solo mientras haya datos sintéticos; **no** reutilizarlo como base jurídica ni como `#14`. |
| H13 | Pendiente | `#13` (comunicaciones) y `#14` (tratamiento): el real los mezcla en el mismo bloque. | Separar finalidades; `#13` fuera de MVP (la demo no envía comunicaciones). |
| H14 | Exposición | `PersonOut`/`ApplicationSummary` se comparten según `applications.read`, pero los nuevos campos son de riesgo variable. | Mantener protegidos G3/G6 **fuera de listados**; en detalle, **redactar/omitir por grupo** salvo permiso de ámbito más concesión de categoría válida. `applications.read` **no basta** para datos G3/G6. Ver matriz §2.5. |
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
| 5 | Año de nacimiento | `birth_year` / `person.birth_year` | `int`, año calendario plausible | Sí (observado). **No usar** `birth_year <= año actual − 18` como prueba definitiva: quien cumplirá 18 más tarde este año aún es menor. Valorar elegibilidad de forma humana con información suficiente, según necesidad y proporcionalidad | Persona | P + instantánea si se usa en evaluación | ORD | MVP |
| 6 | País de nacimiento | `birth_country` / `person.birth_country` | ISO 3166-1 alfa-2 `str(2)` **propuesto**; cotejar opciones reales | **Sí observado** en el bootcamp; **obligación contractual pendiente Melissa** | Persona | P + instantánea limitada si interviene en revisión | ORD* | MVP sintético; protegido G3 |
| 7 | Nacionalidad | `nationality` / `person.nationality` | ISO 3166-1 alfa-2 `str(2)` **propuesto**; cotejar opciones reales | **Sí observado** en el bootcamp; **obligación contractual pendiente Melissa** | Persona | P + instantánea limitada si interviene en revisión | ORD* | MVP sintético; protegido G3 |
| 8 | Género | `gender` / `person.gender` | **Opciones reales no capturadas por Anas**; IDs propuestos solo como ejemplos, no enum aprobado | **Sí observado** en bootcamp; decidir opciones/alternativas antes de implementar. **No se autorizan cuotas** | Persona (autodeclarado) | P + instantánea limitada si se usa en revisión | ORD* / evaluar contexto | PENDIENTE OPCIONES; protegido G3 |
| 9 | Provincia/distrito de residencia | `residence_region` / `application.answers` | código de provincia (INE) o distrito (PT) | Sí. El requisito de residencia **depende de la convocatoria** (Madrid, Barcelona, online = sin requisito); lo confirma una persona al revisar, no hay exclusión automática | Persona | A | ORD | MVP |
| 10 | Experiencia en programación | `programming_experience` / `application.answers` | texto 1–1500 | Sí (real). No pedir datos sensibles (aviso en UI) | Persona | A | ORD | MVP |
| 11 | Situación actual (varias) | `current_situation` / `application.answers` | lista de IDs por versión | Sí observado, ≥1. `none` excluyente. **Todo el grupo se protege como G6** si incluye discapacidad; sin exposición parcial accidental | Persona (autodeclarado) | A | **ESP?** (p. ej. discapacidad) / ORD* | MVP sintético, acceso explícito |
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
| G3 Origen y género | `#6, #7, #8` | Fundación / responsable funcional por designar | **Pendiente acreditar** finalidad, necesidad y base jurídica | Observados en bootcamp; exigencia de financiador **no documentada** | **Denegado por defecto**, incluso a quien tenga `applications.read`; solo detalle bajo concesión explícita G3 vigente para la convocatoria | No usar para scoring, cuotas ni priorización mientras no se apruebe documentalmente su necesidad y legalidad. Agregados suprimidos según riesgo |
| G4 Residencia | `#9` | Selección | Ídem G1 | Requisito de la convocatoria (Madrid) | Igual G1 | Señal para revisión humana; **sin exclusión automática** |
| G5 Perfil técnico | `#10`, `motivacion` | Selección | Ídem G1 | Valoración humana de itinerario | Igual G1 | Apoya revisión humana |
| G6 Situación personal | `#11` | Fundación / responsable funcional por designar | **Posible art. 9**, requiere art. 6 y excepción art. 9.2 cuando corresponda; pendiente DPO | Autodeclaración; justificar cada opción por convocatoria | **Denegado por defecto**; autorización G6 explícita por usuario, finalidad y convocatoria; solo detalle, nunca listas/logs; agrupaciones sensibles con supresión | Solo información para revisión humana si criterios formalmente aprobados; no criterio automático de exclusión ni ranking |
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
| Supresión | **Propuesta** | Procedimiento conforme a la Fundación; los IDs de `audit_event` **pueden ser datos personales seudonimizados**. Retención y eventual disociación sujetas a justificación; el trigger append-only no autoriza conservación indefinida. |
| Datos de formulario sensibles | **Propuesta** | Plazo igual o menor que el general; revisión por DPO |

### 2.5 Política de acceso por grupo, rol y convocatoria — DISEÑO V2

La existencia de `role_assignment` (rol + ámbito) en `dev` **no significa que estén implementados** el filtrado de grupos de campos, la gestión de concesiones ni una pantalla de permisos. Para implementarlos, véanse la [especificación de acceso dinámico](kan-107-6-control-acceso-dinamico.md) y el Entregable 4.

| Grupo | Contenido | Acceso base a la candidatura | Grupo protegido adicional | Política recomendada |
|---|---|---|---|---|
| G1/G2 | Identificación, contacto y edad | Captación o selección en convocatoria/programa autorizado; admin operacional según tarea | No, pero nunca público ni fuera de ámbito | Solo mínimos por finalidad y pantalla |
| G4/G5/G7 | Residencia, experiencia, canal y motivación autorizada | Captación o selección en ámbito correcto | No, pero ocultar datos no necesarios en listados | Nunca decisión automática |
| G3 | País de nacimiento, nacionalidad y género | `applications.read` **necesario pero insuficiente** | **Sí:** concesión G3 explícita vigente en la convocatoria | Redactado/omitido por defecto; no cuota automática |
| G6 | Situaciones personales, incluida discapacidad | `applications.read` **necesario pero insuficiente** | **Sí:** concesión G6 explícita vigente | Proteger `current_situation` completo si alguna opción revela categoría especial |
| G8/G9 | Aceptación informativa, referencias técnicas, eventos y auditoría | Según finalidad y operación | Auditoría interna solo para perfiles con `audit.read` | Nunca incluir valores personales en registros |

**Cambios de permiso durante la convocatoria:** administrador autorizado y con aprobación funcional concede/revoca G3/G6 para una persona concreta y una `call_id`; incluir vigencia/revocación inmediata, razón y auditoría de acceso y cambio. Nadie puede concederse a sí mismo acceso. El rol administrativo **no implica lectura automática** de G3/G6. Esta es una **capacidad propuesta para KAN-42**, no implementada por KAN-107. La persona solicitante puede ejercer sus derechos a través del procedimiento que establezca la Fundación, distinto del portal de personal.

**EN:** Sensitive field groups require both an existing scoped application permission and an additional time-bound per-call grant. Grants/revocations during an active call must be authorised, logged, immediately enforced and never self-issued; these controls are proposed, not implemented.

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

Criterio de reparto: **ficha actual de la persona → `Person`; declaraciones y reglas usadas para una candidatura → instantánea mínima y protegida en `Application`**. Los datos pueden rectificarse y su conservación está limitada por la finalidad. No congelar indiscriminadamente todos los atributos de `Person`.

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
| [KAN-92](https://anasfady87-1789923749606.atlassian.net/browse/KAN-92), [KAN-93](https://anasfady87-1789923749606.atlassian.net/browse/KAN-93), [KAN-107](https://anasfady87-1789923749606.atlassian.net/browse/KAN-107), [KAN-112](https://anasfady87-1789923749606.atlassian.net/browse/KAN-112) | **Contrastados por revisor el 17/11/2026** | KAN-93 contiene decisiones PO sobre campos y obligatoriedad; no hay aprobación de cuotas ni requisitos contractuales |
| AS-IS y aclaraciones de Melissa (Drive) | **No accesible** | **Bloqueo B2**: se cita lo que recoge el documento de Anas (06 y 08/11/2026) |
| Formulario real Somos F5 | **No re-consultado**; se usa la captura de Anas del 17/11/2026 | — |
