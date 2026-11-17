# KAN-107 · Entregable 3 — Evaluación de privacidad / Privacy assessment

**Estado:** análisis técnico-funcional preliminar. **No sustituye al DPO ni al asesoramiento jurídico de la Fundación.** No declara que ningún tratamiento sea lícito, ilícito ni que la EIPD sea obligatoria.
> **EN summary:** Risk matrix for the application form. Nationality, birth country and gender are kept (PO decision 17/11/2026); this document records the risk, the alternative, and who must authorise. Disability is treated as a probable special-category (health) datum.

## 1. Fuentes y su uso

> **Aviso de verificación:** en esta sesión **no se ha podido consultar en línea** el BOE, EUR-Lex ni la web de la AEPD. Las referencias siguientes se citan por su identificación habitual y **deben verificarse** contra el texto oficial antes de usarse fuera del equipo (**Bloqueo B3**).

| Fuente | Referencia | Para qué se usa aquí | Tipo |
|---|---|---|---|
| RGPD — Reglamento (UE) 2016/679 | Art. 4 (definiciones, incl. datos relativos a la salud), 5 (principios: minimización, limitación de finalidad, limitación del plazo), 6 (bases de licitud), 7 (condiciones del consentimiento), 9 (categorías especiales), 13 (información), 22 (decisiones automatizadas), 25 (privacidad desde el diseño y por defecto), 32 (seguridad), 35 (EIPD) | Requisitos jurídicos | **Requisito legal** |
| LOPDGDD — Ley Orgánica 3/2018 | Arts. relativos a tratamiento de categorías especiales, derechos y deber de información por capas | Requisitos jurídicos nacionales | **Requisito legal** |
| AEPD | Guías sobre privacidad desde el diseño y por defecto, sobre EIPD, y lista de tratamientos que requieren EIPD (art. 35.4) | Metodología y criterio de la autoridad | **Recomendación** (la lista de la AEPD se aplica como criterio de la autoridad) |
| Documentos del repositorio | `CONSTITUTION.md`, `AGENTS.md`, ADR-0003 | Reglas del proyecto (datos sintéticos, revisión humana, RBAC por ámbito) | Política interna |

## 2. Naturaleza de los datos

| Dato | Calificación preliminar | Razonamiento |
|---|---|---|
| Nombre, apellidos, correo, teléfono, año de nacimiento, provincia | Ordinario | Identificación/contacto; riesgo bajo-medio |
| Nacionalidad, país de nacimiento | Ordinario, **no categoría especial automáticamente**; riesgo de actuar como *proxy* de origen étnico/racial | Evaluar finalidad y contexto; puede facilitar discriminación indirecta |
| Género | Ordinario según el contexto; no es art. 9 por sí mismo. Atención a opciones como `non_binary`/`other` en contextos que puedan revelar orientación o identidad de género | Opcional + `prefer_not_to_say`; solo estadística |
| "Situación actual": discapacidad | **Probable dato relativo a la salud (art. 9)** | Requiere condición adicional del art. 9.2, **a determinar por DPO** |
| "Situación actual": inmigrante, refugiada/o, riesgo de exclusión, mujer en situación de vulnerabilidad, acceso limitado a recursos | **A evaluar**: pueden revelar condición socioeconómica o, según el caso, origen étnico/racial o convicciones; no se puede decidir sin análisis de contexto | Tratar con las mismas medidas que art. 9 por precaución (decisión de diseño, no afirmación jurídica) |
| Disponibilidad, experiencia, canal | Ordinario | — |

## 3. Matriz de riesgos

Probabilidad (P) e impacto (I): B/M/A. Estado: ABIERTO · MITIGADO EN DISEÑO · PENDIENTE DE DECISIÓN.

| ID | Riesgo | P | I | Mitigación propuesta | Quién autoriza | Estado |
|---|---|---|---|---|---|---|
| R1 | Recogida **excesiva** (campos sin finalidad acreditada: motivación, país de nacimiento, canal) | M | M | Cada campo con finalidad (Entregable 1 §2.3); `opcional` por defecto cuando no sea exigencia del financiador | PO + Fundación | PENDIENTE |
| R2 | **Base jurídica no confirmada** para el tratamiento; confusión entre "casilla" y consentimiento | A | A | No usar la casilla `#14` como base; registrar versión de aviso y fecha; determinar base con DPO. Consentimiento explícito solo donde proceda (p. ej. comunicaciones `#13`, y posible excepción art. 9.2.a para datos especiales) | Fundación / DPO | PENDIENTE |
| R3 | **Mantener nacionalidad, país de nacimiento y género** (decisión PO): sin exigencia acreditada del financiador | M | M | Alternativa recomendada si no hay exigencia: no pedirlos o hacerlos **opcionales** (minimización art. 5.1.c y 25). Si se mantienen: finalidad **solo estadística/equidad**, acceso restringido, **fuera de preselección** | **PO decide; Fundación/DPO autoriza**; Melissa confirma exigencia del financiador | PENDIENTE (decisión PO respetada, riesgo documentado) |
| R4 | **Discapacidad** y otras opciones de `#11` (art. 9) | M | A | Opción informada; acceso con permiso específico `applications.read_sensitive`; nunca en listados ni logs; no usar para exclusión; excepción art. 9.2 identificada por DPO antes de recoger datos **reales** | DPO / Fundación | PENDIENTE |
| R5 | **Decisión automatizada** sobre personas | B | A | Reglas de convocatoria (p. ej. residencia Madrid) solo *señalan* para revisión humana; admisión siempre humana (`pendiente_decision_humana`; art. 22) | PO | MITIGADO EN DISEÑO |
| R6 | **Exposición horizontal**: un usuario de otra convocatoria/programa ve fichas ajenas | M | A | Alcance servidor `Scope(program_id, call_id)` ya existe (`authz.py`); tests de acceso horizontal para endpoints nuevos | Backend | MITIGADO PARCIALMENTE (tests de ámbito existen; faltan los de campos sensibles) |
| R7 | **Datos sensibles en notas CRM** (`application_event.resumen`) | M | A | Aviso ya presente en `EventCreate.resumen`; propuesta: lista de comprobación y formación de usuarios; evaluación posterior de detección | Selección / DPO | ABIERTO |
| R8 | **Datos sensibles en logs** | B | A | No existe logging propio hoy; antes de añadirlo: filtro que prohíba `answers` y campos G3/G6; `audit_event.meta` solo IDs/códigos | Backend | MITIGADO EN DISEÑO (a verificar con test) |
| R9 | **Sin plazo de retención** definido | A | M | Fijar `[N meses]` con la Fundación; job de borrado/anonimización posterior | Fundación | PENDIENTE |
| R10 | **Estadísticas reidentificables** (grupos pequeños) | M | M | Supresión ya implementada: `min_group_size=5`, `min_cell_size=3` en `GET /calls/{id}/summary`; aplicar igual a cualquier agregado de datos sensibles | Backend | MITIGADO (código presente; test existente) |
| R11 | **Sesgo/discriminación indirecta** por proxy (nacionalidad, residencia, género) | M | A | No usar G3/G6 como entrada de ranking; si entra IA/ML en el futuro: evaluación específica (fuera de KAN-107; dropout ML es otro alcance) | Fundación / equipo ML | ABIERTO |
| R12 | **Menores**: `birth_year` permitiría edades <18 | B | A | Validar rango mínimo de edad que fije la Fundación (valor **pendiente**); no asumir 18 | Fundación | PENDIENTE |
| R13 | **Rectificación/supresión** de datos en versiones históricas | M | M | Procedimiento de derechos; respuestas congeladas con evento de rectificación; supresión con borrado de `answers` y `person` conservando `audit_event` sin datos personales | Fundación / DPO | PENDIENTE |
| R14 | **Datos reales introducidos por error** en el entorno de demo | M | A | `is_synthetic`, aviso `acepta_datos_sinteticos`, dominios reservados en demo | Equipo | MITIGADO PARCIALMENTE |

## 4. ¿Hace falta una EIPD?

**No se declara obligatoria.** Señales que justifican analizarla antes de tratar **datos reales** (art. 35): posible tratamiento de datos de categorías especiales (R4), colectivos en situación de vulnerabilidad, y uso del dato para valorar a personas. Lo hace la Fundación con su DPO usando la lista de tratamientos de la AEPD (art. 35.4) y el art. 35.3. **Con datos sintéticos no hay tratamiento de datos personales reales**, por lo que no se bloquea el desarrollo, pero sí la puesta en producción.

## 5. Requisitos jurídicos frente a recomendaciones

| Tipo | Elemento |
|---|---|
| **Requisito jurídico** (a verificar con DPO) | Base de licitud identificada (art. 6) y, para categorías especiales, condición del art. 9.2; información al interesado (art. 13); minimización y limitación de finalidad (art. 5); privacidad por defecto (art. 25); seguridad (art. 32); límites a decisiones automatizadas (art. 22) |
| **Recomendación de diseño** | Campos opcionales por defecto; `prefer_not_to_say`; permiso `applications.read_sensitive`; sensibles fuera de listados y logs; versiones de formulario inmutables; revisión humana de toda admisión; supresión de agregados pequeños |
| **Política del proyecto** | Solo datos sintéticos; RBAC por rol+ámbito; auditoría append-only |

## 6. Decisiones pendientes de la Fundación (Melissa / DPO)

| # | Pregunta | Afecta a |
|---|---|---|
| D1 | ¿Quién es responsable del tratamiento y cuál es la base de licitud (art. 6) del tratamiento de candidaturas? | `#14`, todo |
| D2 | ¿El financiador **exige** nacionalidad, país de nacimiento y género? ¿Con qué finalidad y nivel de detalle? | R3, `#6–#8` |
| D3 | ¿Qué opciones de "situación actual" exige cada financiador? ¿Cuáles implican datos del art. 9 y con qué excepción se tratan? | R4, `#11` |
| D4 | ¿Plazos de conservación (no admitidas / admitidas)? | R9 |
| D5 | ¿Edad mínima para participar? | R12 |
| D6 | ¿Quién puede ver datos sensibles (qué roles y ámbitos)? | permiso `applications.read_sensitive` |
| D7 | ¿Se necesita EIPD antes de usar datos reales? ¿La hace la Fundación? | §4 |
| D8 | ¿`motivacion` se mantiene como pregunta propia? | H11 |
| D9 | ¿La regla de residencia (Madrid) es criterio de revisión o de elegibilidad? | R5, KAN-112 |
