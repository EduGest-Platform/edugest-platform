# KAN-107 · Entregable 1 — Diccionario de datos consolidado / Consolidated data dictionary

**Estado:** revisión documental V2 para aprobación PO/Anas (no es validación jurídica ni código implementado) · **Fecha base:** 17/11/2026 · **Reconciliación:** 18/11/2026 · **Ubicación de entrega:** Diseño KAN-107, rama documental `docs/KAN-107-data-governance` hacia `dev`.
**Base reutilizada:** [inventario canónico KAN-92/93](https://github.com/EduGest-Platform/edugest-platform/blob/d59ee8cde39773af9fc041544a2346ec4ab5245d/docs/producto/diccionario-campos-candidatura.md) de Anas, integrado en `dev` por PR #27; copia retirada del PR #15. Contraste: 18/11/2026, `origin/dev` `d59ee8c`. Las filas `#1–#14` se refieren al Formulario A; B contiene diferencias capturadas el 18/11 y C es una descripción del equipo todavía sin URL/verificación. KAN-92/93 mantiene el inventario observado; este documento añade gobierno y decisiones propuestas, sin sustituirlo.

> **EN summary:** Technical + functional dictionary for the 14 fields of the real Somos F5 form plus EduGest-only fields. Each field has an owner entity (Person vs Application), a stable technical id, a proposed legal-basis *candidate* (all pending confirmation by the Foundation/DPO), access scope and status. Nothing here changes code, models or contract yet.


## Decisión PO aceptada el 18/11/2026 / PO decision accepted on 18/11/2026

**ES — Alcance aceptado para el diseño sintético.** La referencia del MVP es el **Bootcamp de Desarrollo de IA de 1.250 h**, con candidatura y selección humana. Mayoría de edad para esta convocatoria y edad configurable para otras. Residencia obligatoria en Comunidad de Madrid por el requisito publicado. Pedir conocimientos/experiencia de programación incluyendo formación y autoaprendizaje, **sin exigir experiencia profesional**. **Motivación inicial opcional**, profundizada en entrevista. Informar de dedicación intensiva y mantener disponibilidad opcional inicialmente. El cambio de motivación no está implementado: API/BD aún la exigen.

**Evidencia:** texto público de las páginas oficiales del [bootcamp 1.250 h](https://landings.somosf5.org/proyecto-ai4inclusion-bootcamp) y [curso 15 h](https://landings.somosf5.org/proyecto-ai4inclusion-curso15h) consultado el 18/11/2026. La primera también publica desempleo y permiso de trabajo, contemplando valoración individual del permiso en trámite. Esta aceptación no añade campos ni carga de justificantes. Los campos del formulario incrustado no aparecen en el contenido recuperado y no se han vuelto a verificar. B es otra formación y no define el formulario base del bootcamp.

**Resuelto el 19/11** (ver «Decisiones PO del 19/11/2026»): fecha de comprobación de edad, «más de 16», destino de opciones de B, formulario C, canal, residencia en otras convocatorias y ventana de gracia. La aceptación de estas recomendaciones no sustituye la revisión de Anas ni la aceptación final de KAN-107.

**EN — Accepted synthetic design.** The 1,250-hour AI bootcamp remains the MVP reference: adulthood, mandatory published Madrid residence, training/self-study as programming background, optional initial motivation and availability. API/DB still require both fields. The 19 November decision below resolves age reference/operator, B routing, referral source, residence configuration, grace window and G3/G6 access for synthetic design. This is not Foundation legal validation or final cross-review.


## Decisiones PO del 19/11/2026 / PO decisions of 19/11/2026

**ES — Decididas por la PO (Elizabeth) el 19/11/2026.** Son decisiones de diseño; ninguna está implementada en API/BD por este paquete (la implementación es KAN-42 y la historia que corresponda).

| Tema | Decisión |
|---|---|
| Motivo de las revisiones de requisitos (KAN-128) | **Motivo codificado** de una lista cerrada, sin datos sensibles, visible para todos los perfiles con acceso; **nota libre opcional** solo visible para admisión (captación, selección) y administración, manteniendo el aviso de no incluir datos sensibles |
| Curso de 15 h (formulario B) | **Mixto:** cada fecha concreta crea una candidatura en su convocatoria (`call_id`); «Quiero organizar un curso» y «Avísame de próximas fechas» crean una **solicitud de contacto**, no una candidatura |
| Fecha de comprobación de la edad | **Inicio del curso.** Con solo el año de nacimiento, los casos dudosos van a revisión humana; nunca exclusión automática |
| «Más de 16 años» (curso de 15 h) | **16 años o más** (operador `gte`, 16) |
| Ventana de gracia al cambiar la versión del formulario | **24 horas** desde `effective_from` de la nueva versión (su activación; si se aprueba con efecto inmediato, `approved_at`); después se pide rellenar la nueva. Ver Entregable 2, regla 7. **Marca de tiempo confirmada por la PO el 20/11/2026** |
| Acceso a datos G3/G6 en el MVP | **Administración y selección** los ven por defecto; **administración puede conceder o retirar** ese acceso a otros perfiles, con auditoría |
| Formulario C | **Fuera del MVP** hasta disponer de URL o captura; el certificado de discapacidad sigue clasificado G6 |
| «¿Cómo nos conociste?» | **Obligatorio**, como en el formulario real |
| Residencia en otras convocatorias | **Configurable por convocatoria** según lo publicado; revisión humana, sin exclusión automática |

**EN — Decided by the PO on 19/11/2026 (design only; not implemented by this package).** KAN-128 reasons: closed coded reason visible to all in-scope profiles plus an optional free-text note visible only to admissions staff and admin. 15-hour course: each concrete date creates an application in its call; "organise a course" and "notify me" create a contact request. Age is checked at course start (year-only cases go to human review). "Over 16" means 16 or older. 24-hour grace window for form version changes. G3/G6 data: admin and selection by default; admin can grant or revoke access for other profiles, audited. Form C out of the MVP. "How did you hear about us" stays mandatory. Residence is configured per call.

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
| "Cómo nos has conocido" | **PO 19/11:** obligatorio; sustituye la propuesta histórica de hacerlo opcional |
| Edad mínima | **PO 19/11:** al inicio del curso; bootcamp mayoría de edad, B `gte` 16. Solo el año requiere revisión humana. No es validación del requisito real por la Fundación |
| Residencia | Depende de la convocatoria (Madrid, Barcelona, online). Se pide siempre; lo confirma una persona |
| Quién ve los datos | Administración y selección: acceso por defecto dentro del ámbito autorizado. Otros perfiles: permiso base más concesión G3/G6 vigente por usuario y convocatoria, concedida/revocada por administración y auditada. Solo detalle, nunca listas ni logs. Decisión PO 19/11; no implementada. La decisión posterior de acceso/tablero amplía coordinación; su matriz deberá reconciliarse y probarse en las tareas correspondientes |
| Rectificación/borrado | Llegan por correo. Proceso **pendiente** (fuera del alcance de la prueba de concepto) |
| Responsable del tratamiento y DPO | **Pendiente**; se deja anotado en el README, no se resuelve ahora |
| Revisión legal (RGPD/LOPDGDD/AEPD) | **Fuera del alcance** del proyecto (gratuito, datos sintéticos); corresponde a la Fundación en una fase posterior |

### Evidencia reconciliada del curso de 15 h (18/11/2026)

El inventario canónico KAN-92/93 §4 documenta una captura en vivo del Formulario B: una etapa, campos comunes con A, selector de curso/fecha (`call_id` propuesto), acceso a ordenador/internet, sin pregunta de experiencia en programación. Incluye año de nacimiento, género y situación actual; teléfono obligatorio según los campos comunes.

La imagen de baja resolución del 17/11 sugería contacto, ciudad y teléfono opcional. Se conserva como antecedente **no concluyente**, superado para describir B por la captura del 18/11. No se ha vuelto a consultar la landing en esta revisión.

**DECIDIDO PO 19/11 (ver arriba):** fecha concreta → candidatura; organizar curso / avisar de fechas → solicitud de contacto. Antes figuraba como pendiente: confirmar si coexisten formularios de contacto e inscripción y el destino de cada opción del selector (curso concreto, organizar curso, avisar de fechas). Se retira la decisión categórica de un modelo separado `Lead/ContactRequest` y de que el curso nunca crea `Application`. El mapeo de cursos concretos a candidatura por `call_id` es una propuesta del inventario, no implementación ni aceptación de todas las opciones como candidaturas.

El bootcamp A sigue como referencia inicial del MVP, sujeto al mínimo común que cierre la PO. No introducir `city`, asumir experiencia obligatoria en B ni unificar finalidades sin validación; C describe municipio/comunidad autónoma y sigue pendiente de fuente.

## 1. Auditoría del inventario (qué falta, qué se duplica, qué choca)

### 1.1 Estado en `dev` (inspección estática, 18/11/2026, `d59ee8c`; schema revisado el 19/11/2026 en `c59d201`; CODE_PRESENT_NOT_RUN)

| Elemento | Dónde | Hoy |
|---|---|---|
| `ApplicationCreate`: `call_id, nombre, email, motivacion, disponibilidad, acepta_datos_sinteticos` | `api/app/modules/admissions/schemas.py` | 6 campos |
| `Person`: `display_name, email, legacy_ref, is_synthetic, created_at` | `api/app/modules/identity/models.py` | 1 solo nombre |
| `Application`: `codigo, legacy_ref, person_id, call_id, stage, motivacion, disponibilidad (NOT NULL), acepta_datos_sinteticos` | `api/app/modules/admissions/models.py` | sin versión de formulario |
| `Call`: `id, program_id, nombre, codigo_prefix, opens_on, closes_on, plazas, estado, next_seq, silence_days, silence_max_contacts, silence_warning_contacts` | `api/app/modules/catalog/models.py` | Política de silencio integrada con KAN-153; no hay versión de formulario |
| `CallRequirement` (`call_requirement`, KAN-135, migración `0006`): `ref, code, version, label, kind, funder` inmutables por convocatoria | `api/app/modules/requirements/models.py` | requisitos configurados, no campos del formulario |
| `RequirementReview` / `RequirementReviewRevision` (KAN-128, migración `0004`): resultado y `reason` de texto libre (500) por requisito | `api/app/modules/requirements/models.py` | ver Entregable 6, interacción con KAN-128 |
| Contrato | `contracts/openapi.json` (`ApplicationCreate`, `ApplicationDetail`…) | refleja lo anterior |
| Logging | `api/app/core/error_handling.py`, `api/app/main.py`, `api/docker-entrypoint.sh` | KAN-105 (#23) integrado: `app.access`, request IDs de servidor, rutas parametrizadas y errores seguros; Uvicorn con `--no-access-log`; #29 evita relanzar excepciones tras iniciar respuesta. Inspección estática, sin certificación runtime de todos los sinks; auditoría funcional separada |

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
| H11 | Pendiente | `motivacion` **no existe en el formulario real** (el real pide experiencia, `#10`). | **PO 18/11:** motivación inicial opcional en diseño, profundizada en entrevista. Mientras no se implemente, `motivacion` **sigue siendo obligatoria** en el contrato actual (`schemas.py`, `NOT NULL`). |
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
| 5 | Año de nacimiento | `birth_year` / `person.birth_year` | `int`, año calendario plausible | Sí (observado). **Requisito por convocatoria/versionado (propuesta):** A, mayoría de edad; B, **más de 16 años**, que la PO interpretó el 19/11 como **16 o más** (`gte` 16), comprobado al inicio del curso. Guardar umbral, operador y fecha de referencia aprobados. **No usar solo el año como prueba definitiva** de cumplimiento del umbral. Valorar elegibilidad de forma humana con información suficiente, según necesidad y proporcionalidad | Persona | P + instantánea si se usa en evaluación | ORD | MVP |
| 6 | País de nacimiento | `birth_country` / `person.birth_country` | ISO 3166-1 alfa-2 `str(2)` **propuesto**; cotejar opciones reales | **Sí observado** en el bootcamp; **obligación contractual pendiente Melissa** | Persona | P + instantánea limitada si interviene en revisión | ORD* | MVP sintético; protegido G3 |
| 7 | Nacionalidad | `nationality` / `person.nationality` | ISO 3166-1 alfa-2 `str(2)` **propuesto**; cotejar opciones reales | **Sí observado** en el bootcamp; **obligación contractual pendiente Melissa** | Persona | P + instantánea limitada si interviene en revisión | ORD* | MVP sintético; protegido G3 |
| 8 | Género | `gender` / `person.gender` | A: opciones no capturadas; B: Mujer, Hombre, Otro (No binario), Prefiero no identificarme. C: lista distinta descrita en el inventario §5, sin verificar; no unificar enums entre formularios | **Sí observado** en bootcamp; decidir opciones/alternativas antes de implementar. **No se autorizan cuotas** | Persona (autodeclarado) | P + instantánea limitada si se usa en revisión | ORD* / evaluar contexto | OPCIONES POR VERSIÓN; C pendiente; protegido G3 |
| 9 | Provincia/distrito de residencia | `residence_region` / `application.answers` | código de provincia (INE) o distrito (PT) | Sí (observado). El requisito de residencia **depende de la convocatoria**; lo confirma una persona al revisar, sin exclusión automática. **Justificación en convocatorias sin requisito territorial (p. ej. online):** el equipo decidió pedirlo siempre; solo se sostiene si hay finalidad documentada (logística presencial o estadística agregada). **Propuesta pendiente de PO:** `required` por versión de formulario; si la convocatoria no tiene requisito territorial ni finalidad documentada, no se incluye el campo (minimización). Ver §2.1b | Persona | A | ORD | MVP |
| 10 | Experiencia en programación | `programming_experience` / `application.answers` | texto 1–1500 | Sí (real). No pedir datos sensibles (aviso en UI) | Persona | A | ORD | MVP |
| 11 | Situación actual (varias) | `current_situation` / `application.answers` | lista de IDs por versión | Sí observado, ≥1. `none` excluyente. **Todo el grupo se protege como G6** si incluye discapacidad; sin exposición parcial accidental | Persona (autodeclarado) | A | **ESP?** (p. ej. discapacidad) / ORD* | MVP sintético, acceso explícito |
| 12 | ¿Cómo nos conociste? (varias) | `referral_source` / `application.answers` | lista de IDs | **Observado: obligatorio** (inventario KAN-92/93, A/B). **Decisión PO 19/11: obligatorio** en el MVP, como en el formulario real, con opción `other`. Ver §2.1b | Persona | A | ORD | MVP |
| 13 | Comunicaciones de Somos F5 | `marketing_opt_in` | `bool` | No | Persona | P (con fecha y versión de texto) | ORD | POSTERIOR |
| 14 | Información/consentimiento de tratamiento | `privacy_notice_version`, `privacy_notice_ack_at` / `application` | `str` + `datetime` | Sí. **Es acuse de información (art. 13), no se presume base jurídica** (H12) | Persona | A | TEC | MVP |

### 2.1b Obligatoriedad campo por campo: observado frente a decidido

Separa lo **OBSERVADO** en el formulario real (inventario canónico KAN-92/93, Formulario A salvo indicación) de lo **DECIDIDO/PROPUESTO** para el MVP. Donde difieren, queda dicho por qué y quién debe ratificarlo. La tabla 2.1 resume; esta tabla manda en caso de duda.

| # | Campo | Observado (real) | MVP propuesto | ¿Difiere? | Justificación / estado |
|---|---|---|---|---|---|
| 1–2 | Nombre, apellidos | Obligatorio | Obligatorio | No | Separar en `first_name`/`last_name` (decisión PO) |
| 3 | Correo | Obligatorio | Obligatorio | No | Ya existe |
| 4 | Teléfono | Obligatorio | Obligatorio | No | Recordatorios y llamadas (AS-IS) |
| 5 | Año de nacimiento | Obligatorio | Obligatorio | No | Requisito configurable por convocatoria: A mayoría de edad, B >16; configuración y mayoría de edad bootcamp aceptadas PO; **PO 19/11:** comprobación al inicio del curso y B = 16 o más; año insuficiente y revisión humana |
| 6–8 | País de nacimiento, nacionalidad, género | Obligatorio | Obligatorio (sintético) | No | Decisión PO de mantenerlos; exigencia del financiador **no documentada** (pendiente Melissa); acceso G3 protegido; sin cuotas |
| 9 | Residencia | Obligatorio | Obligatorio con requisito territorial; **propuesta:** no incluir o hacer opcional sin él | **Propuesta** | Respuesta del equipo: se pide siempre. Sin requisito territorial solo se justifica con finalidad documentada. **PO 19/11:** configurable por convocatoria según lo publicado |
| 10 | Experiencia en programación | Obligatorio en A; ausente en B y no confirmado en C | Por versión; mínimo común pendiente PO | Sí entre formularios | No exigir en B por herencia de A; `motivacion` sigue obligatoria en API hasta implementar la decisión PO de hacerla opcional |
| 11 | Situación actual | Obligatorio (≥1) | Obligatorio (≥1) | No | G6 protegido; opciones por convocatoria |
| 12 | ¿Cómo nos conociste? | **Obligatorio** | **Obligatorio** | No | **PO 19/11:** se mantiene obligatorio (sustituye la propuesta del equipo del 17/11 de hacerlo opcional) |
| 13 | Comunicaciones | Opcional | Fuera de MVP | — | La demo no envía comunicaciones |
| 14 | Información/tratamiento | Obligatorio | Obligatorio (acuse art. 13) | No | No se presume base jurídica |
| — | `motivacion` | No existe en el real | **Opcional en diseño (PO 18/11)**; hoy obligatoria en contrato | **Sí** | Cambio incompatible pendiente de implementar en KAN-42; el contrato actual sigue obligatorio |
| — | `disponibilidad` | No existe en el real | Opcional | Sí | Decisión PO 17/11; cambio incompatible H9 |

### 2.1c Diferencias de B/C fuera de las 14 filas de A

El inventario KAN-92/93 es la fuente de opciones y obligatoriedad; estos destinos son **PROPOSED**, no campos implementados ni alcance aceptado.

| Campo | Evidencia | Destino técnico propuesto | Grupo / tratamiento | Estado |
|---|---|---|---|---|
| Curso/fecha | B §4, obligatorio | Fecha concreta: `call_id`; organizar/avisar: solicitud de contacto | G9; no fabricar candidatura para avisos | PO 19/11; sin implementar |
| Acceso a ordenador/internet | B §4, obligatorio; no excluye | `application.answers.computer_access` | G5, apoyo/logística, nunca exclusión automática | Pendiente mínimo común PO |
| Certificado de discapacidad | C §5, sin URL; obligatoriedad pendiente | `application.answers.disability_certificate_status`, opción declarada, **no subida de certificado** | **G6**, dato de salud, misma concesión explícita, omisión en listas/logs/exportaciones; necesidad y tratamiento real pendientes | PENDIENTE; no activar por defecto |
| Entidad que deriva | C §5, texto obligatorio descrito | `application.answers.referring_entity` | **G6 por precaución**: puede revelar situación vulnerable/salud por la entidad; no confundir con canal genérico G7 | PENDIENTE fuente, finalidad y alcance PO |
| Municipio/comunidad autónoma | C §5, sin verificar | Campos por versión en `answers` | G4; no exigirlos globalmente | PENDIENTE |

### 2.2 Campos propios de EduGest

| Funcional | Técnico | Tipo | Obligatorio | Entidad | Cat. | Estado / nota |
|---|---|---|---|---|---|---|
| Convocatoria | `call_id` (existe) | `str(30)` FK | Sí | A | TEC | MVP (existe) |
| Versión del formulario aplicada | `form_version_id` (nuevo) | FK `form_version.id` | Sí en altas nuevas | A | TEC | MVP (Entregable 2) |
| Disponibilidad | `disponibilidad` (existe) | `Mañana\|Tarde\|Flexible` | **No** (PO 17/11) | A | ORD | MVP (cambio incompatible H9) |
| Motivación | `motivacion` (existe) | texto 10–2000 | **Hoy OBLIGATORIO en el contrato actual** (`ApplicationCreate.motivacion` 10–2000, columna `NOT NULL`, tanto en `feat/gistar-foundation` como en `dev`). **Decisión PO 18/11:** motivación inicial opcional, profundizada en entrevista. Cambio incompatible (§4) pendiente de implementar en KAN-42; el contrato actual sigue obligatorio | A | ORD | Obligatorio hoy; opcional aceptado en diseño, sin implementar |
| Aviso de datos sintéticos | `acepta_datos_sinteticos` (existe) | `Literal[True]` | Sí mientras haya demo | A | TEC | Retirar en producción real |
| Código de candidatura | `codigo` (existe) | `str(20)` único | Auto | A | TEC | MVP (existe) |
| Etapa | `stage` (existe) | enum de 9 valores | Auto | A | TEC | Existe; las decisiones de admisión son **humanas** |
| Referencia legado | `legacy_ref` (existe) | `str(20)` | Auto | P/A | TEC | Solo datos semilla |
| Marca sintética | `is_synthetic` (existe) | `bool` | Auto | P | TEC | Existe |
| Eventos CRM | `application_event.resumen` (existe) | `str(500)` | — | A | ORD | Ya avisa: "No incluir datos de salud…". Ver R7 |

### 2.3 Gobierno por campo (resumen agrupado)

Agrupado por perfil de riesgo para no repetir 24 filas idénticas; cada campo hereda la fila de su grupo.

| Grupo | Campos | Responsable funcional (propuesto) | Base jurídica *candidata* (pendiente) | Necesidad y proporcionalidad | Acceso (rol · ámbito) | Preselección / estadística / decisión humana |
|---|---|---|---|---|---|---|
| G1 Identificación y contacto | `#1–#4`, `email` | Captación (PO decide) | Art. 6.1 (b ó f ó e según naturaleza de la Fundación) — **confirmar** | Necesario para contactar y gestionar la candidatura | `applications.read`: admin global · captación programa · selección convocatoria. Coordinación y docente: **no** | Contacto; no entra en estadísticas nominales |
| G2 Edad | `#5` | Selección | Ídem G1 | Año para requisito por convocatoria; no prueba exacta ni criterio de financiador acreditado | Igual G1 | Preselección **informativa**; estadística agregada |
| G3 Origen y género | `#6, #7, #8` | Fundación / responsable funcional por designar | Finalidad/base jurídica pendientes para datos reales | Necesidad y proporcionalidad pendientes | Administración y selección: acceso por defecto dentro del ámbito autorizado. Otros perfiles: permiso base más concesión G3/G6 vigente por usuario y convocatoria, concedida/revocada por administración y auditada. Solo detalle, nunca listas ni logs. Decisión PO 19/11; no implementada. | Sin scoring, cuotas o prioridades no aprobadas |
| G4 Residencia | `#9` | Selección | Ídem G1 | Requisito de la convocatoria (Madrid) | Igual G1 | Señal para revisión humana; **sin exclusión automática** |
| G5 Perfil técnico | `#10`, `motivacion`, `computer_access` (B, propuesto) | Selección | Ídem G1 | Valoración humana de itinerario | Igual G1 | Apoya revisión humana |
| G6 Situación personal | `#11`; C fuera del MVP | Fundación / responsable funcional por designar | Base jurídica/condición art. 9 si procede pendientes | Justificar cada opción | Administración y selección: acceso por defecto dentro del ámbito autorizado. Otros perfiles: permiso base más concesión G3/G6 vigente por usuario y convocatoria, concedida/revocada por administración y auditada. Solo detalle, nunca listas ni logs. Decisión PO 19/11; no implementada. | Revisión humana; sin ranking/exclusión automáticos |
| G7 Captación | `#12` | Captación | Ídem G1 | Métrica de canal; no necesaria para decidir | Igual G1 | Solo estadística |
| G8 Información/consentimientos | `#13, #14` | DPO/Fundación | Texto de información art. 13; consentimiento solo donde sea base válida (p. ej. comunicaciones) | — | Registro de versión y fecha; lectura por admin | No |
| G9 Técnicos | `codigo`, `stage`, `form_version_id`, … | Equipo técnico | n/a | n/a | Según endpoint | No |

### 2.4 Retención, modificación y eliminación

Coordinar con [KAN-209 / PR #25](https://github.com/EduGest-Platform/edugest-platform/pull/25): inventario de auditoría, logs operativos, CRM, sesiones, exportaciones y copias. No fijar aquí plazos alternativos. Por conjunto deben aprobarse finalidad, responsable, lectores, ubicación, inicio/plazo y mecanismo de rectificación/supresión. KAN-209/#25 ya está integrado y actualizado tras #23; su observación sobre relanzar errores después de iniciar respuesta queda superada por #29 en `dev` actual. Comprobar siempre el código y todos los sinks. Ninguna purga ni retención de proveedor se ha verificado.

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
| G3 | País de nacimiento, nacionalidad y género | `applications.read` en ámbito | Política PO 19/11: admin/selección por defecto; otros con concesión G3 vigente | Solo detalle autorizado |
| G6 | Situaciones personales; C fuera del MVP | `applications.read` en ámbito | Política PO 19/11: admin/selección por defecto; otros con concesión G6 vigente | Proteger el grupo completo si contiene categorías especiales |
| G8/G9 | Aceptación informativa, referencias técnicas, eventos y auditoría | Según finalidad y operación | Auditoría interna solo para perfiles con `audit.read` | Nunca incluir valores personales en registros |

**Cambios de permiso durante la convocatoria:** Administración y selección: acceso por defecto dentro del ámbito autorizado. Otros perfiles: permiso base más concesión G3/G6 vigente por usuario y convocatoria, concedida/revocada por administración y auditada. Solo detalle, nunca listas ni logs. Decisión PO 19/11; no implementada. Se mantienen finalidad, vigencia y auditoría, sin auto-concesión para otros perfiles. Administrar permisos no sustituye comprobar el ámbito en cada lectura. La ampliación posterior de coordinación se integra en su matriz específica; no se habilita ningún permiso en KAN-107.

**EN:** Admin and selection have default access within their authorised scope. Other profiles need the base permission plus an active user/call/group grant managed by admin and audited. Detail only, never lists or logs. PO decision of 19 November; not implemented.

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
| `motivacion` obligatoria → opcional (diseño aceptado PO 18/11) | `ApplicationCreate` (`min_length=10`), columna `NOT NULL`, `ApplicationDetail.motivacion: str`, `Aspirant.tsx`, seed y tests | Mismo patrón que `disponibilidad`: `DROP NOT NULL` + `str \| None` + regenerar cliente; compatible hacia atrás en lectura. Implementación posterior en KAN-42; esta aceptación documental no modifica el contrato. |
| `answers` JSONB | Consultas SQL por campo | Campos usados en filtros/estadísticas se materializan como columna solo si se demuestra necesidad (no anticipar). |

## 5. Trazabilidad fuente → diccionario

| Fuente | Estado de acceso | Qué se usó |
|---|---|---|
| Inventario canónico KAN-92/93, `docs/producto/diccionario-campos-candidatura.md` | **Leído** en `origin/dev` `d59ee8c`, 18/11/2026; integrado por #27 | A: #1–#14; B: diferencias capturadas 18/11; C: descripción no verificada |
| `schemas.py`, `models.py` (`admissions`, `identity`, `catalog`) | **Leído** en `dev` | §1.1 |
| `contracts/openapi.json` | **Leído** (esquemas `ApplicationCreate`, etc.) | §1.1 |
| [`docs/reports/KAN-109-f1-rbac-regression.md`](../reports/KAN-109-f1-rbac-regression.md) | **Leído** en `dev` (regresión RBAC de F1; la matriz RBAC fechada que se citaba antes no está en `dev`) | Accesos |
| [KAN-92](https://anasfady87-1789923749606.atlassian.net/browse/KAN-92), [KAN-93](https://anasfady87-1789923749606.atlassian.net/browse/KAN-93), [KAN-107](https://anasfady87-1789923749606.atlassian.net/browse/KAN-107), [KAN-112](https://anasfady87-1789923749606.atlassian.net/browse/KAN-112) | **Contrastados por revisor el 17/11/2026** | KAN-93 contiene decisiones PO sobre campos y obligatoriedad; no hay aprobación de cuotas ni requisitos contractuales |
| AS-IS y aclaraciones de Melissa (Drive) | **No accesible** | **Bloqueo B2**: se cita lo que recoge el documento de Anas (06 y 08/11/2026) |
| Formulario real Somos F5 | **Texto público de landings consultado 18/11**; campos incrustados no recuperados. Inventario de campos: capturas A (17/11), B (18/11), C sin verificar | — |

## English edition (equivalent sections, KAN-107 V2)

**Status:** KAN-107 design, documentation branch `docs/KAN-107-data-governance` into `dev`. The canonical observed inventory is Anas's `docs/producto/diccionario-campos-candidatura.md`, merged by PR #27, checked at `origin/dev` `d59ee8c` on 18/11/2026. A contains rows #1–#14; B records live-captured differences; C remains unverified. KAN-107 adds governance without replacing that source.

**§0 How to read.** OBSERVED = field seen in the real form (does not imply a funder requirement); PO DECISION = functional instruction in KAN-93 (not legal validation); Proposal = this analysis, pending approval; Pending = depends on Melissa/Foundation/DPO. All data is synthetic.

**PO decisions already reflected.** Keep nationality, birth country and gender in synthetic design; configurable situation options; optional initial availability/motivation; split first and last name. On 19 November the PO set age at course start (B: at least 16), mandatory referral source, per-call residence, 24-hour compatible-version grace, B course/date vs contact routing, and default admin/selection G3/G6 access. Foundation validation for real data and implementation remain separate. No quotas or automatic exclusion are approved.

**15-hour course form.** The current inventory describes one-stage intake with course/date, computer/internet access and no programming-experience field. PO 19 November: concrete dates create an application; organise/notify create contact requests. Form C is outside the MVP pending a verifiable source.

**§1 Audit.** Findings H1–H15 list gaps between the real form and today's API/DB (missing fields, person vs. application snapshot, `disponibilidad` and `nombre` incompatibilities, `acepta_datos_sinteticos` is not GDPR consent, protected groups must stay out of listings). `motivacion` is **currently mandatory** in the contract (`ApplicationCreate`, `NOT NULL`); optional initial motivation was accepted by PO on 18/11 as design, pending the breaking implementation in KAN-42.

**§2 Field dictionary.** Sections 2.1–2.2 map observed fields to proposed technical names, types, entities and statuses; 2.1b distinguishes observed obligations from PO decisions. Mandatory referral source, age at course start and configured residence follow 19 November decisions. C stays outside MVP; any future certificate/referring entity remains G6. Sections 2.3/2.5: Admin and selection have default access within their authorised scope. Other profiles need the base permission plus an active user/call/group grant managed by admin and audited. Detail only, never lists or logs. PO decision of 19 November; not implemented. Section 2.4 retains Foundation decisions for retention/rectification/erasure, coordinated with KAN-209, without inventing periods or legal approval.

**§3–§5.** Target entities summary, breaking changes with incremental mitigations (including `motivacion`), and source traceability. Nothing here changes code, models, contract or migrations.
