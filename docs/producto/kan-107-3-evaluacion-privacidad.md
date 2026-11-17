# KAN-107 · Entregable 3 — Evaluación de privacidad / Privacy assessment

**Alcance:** el proyecto es una prueba de concepto gratuita con datos sintéticos. La validación legal (base jurídica, EIPD, plazos, responsable y DPO) **queda fuera del proyecto** y corresponde a la Fundación en una fase con datos reales; aquí solo se deja el diseño preparado. **Estado:** análisis técnico-funcional preliminar. **No sustituye al DPO ni al asesoramiento jurídico de la Fundación.** No declara que ningún tratamiento sea lícito, ilícito ni que la EIPD sea obligatoria.
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
| R3 | **Nacionalidad, país de nacimiento y género**: el equipo indica que el financiador los exige; el género puede pesar en cuotas y la vulnerabilidad en prioridades | M | A | Se mantienen como en el formulario real. Mitigación: nunca criterio único ni automático; los criterios de cuota/prioridad se documentan por convocatoria; decide siempre una persona (art. 22); solo en detalle y para el personal de gestión; estadísticas con supresión. La Fundación debe validar con su DPO que ese uso es proporcionado | Fundación / DPO (fase con datos reales) | ABIERTO (decisión del equipo aplicada; validación legal fuera de alcance) |
| R4 | **Discapacidad** y otras opciones de `#11` (art. 9) | M | A | Opción informada; acceso solo con `applications.read` (selección, preselección/captación, administración), solo en detalle; nunca en listados ni logs; no usar para exclusión; excepción art. 9.2 identificada por DPO antes de recoger datos **reales** | DPO / Fundación | PENDIENTE |
| R5 | **Decisión automatizada** sobre personas | B | A | Reglas de convocatoria (p. ej. residencia Madrid) solo *señalan* para revisión humana; admisión siempre humana (`pendiente_decision_humana`; art. 22) | PO | MITIGADO EN DISEÑO |
| R6 | **Exposición horizontal**: un usuario de otra convocatoria/programa ve fichas ajenas | M | A | Alcance servidor `Scope(program_id, call_id)` ya existe (`authz.py`); tests de acceso horizontal para endpoints nuevos | Backend | MITIGADO PARCIALMENTE (tests de ámbito existen; faltan los de campos sensibles) |
| R7 | **Datos sensibles en notas CRM** (`application_event.resumen`) | M | A | Aviso ya presente en `EventCreate.resumen`; propuesta: lista de comprobación y formación de usuarios; evaluación posterior de detección | Selección / DPO | ABIERTO |
| R8 | **Datos sensibles en logs** | B | A | No existe logging propio hoy; antes de añadirlo: filtro que prohíba `answers` y campos G3/G6; `audit_event.meta` solo IDs/códigos | Backend | MITIGADO EN DISEÑO (a verificar con test) |
| R9 | **Sin plazo de retención** definido | A | M | Fijar `[N meses]` con la Fundación; job de borrado/anonimización posterior | Fundación | PENDIENTE |
| R10 | **Estadísticas reidentificables** (grupos pequeños) | M | M | Supresión ya implementada: `min_group_size=5`, `min_cell_size=3` en `GET /calls/{id}/summary`; aplicar igual a cualquier agregado de datos sensibles | Backend | MITIGADO (código presente; test existente) |
| R11 | **Sesgo/discriminación indirecta** por proxy (nacionalidad, residencia, género) y uso de cuotas | M | A | No usar G3/G6 como entrada de un ranking automático; las cuotas y prioridades se aplican por personas y se registran; si entra IA/ML en el futuro: evaluación específica (fuera de KAN-107; dropout ML es otro alcance) | Fundación / equipo ML | ABIERTO |
| R12 | **Menores**: con solo el año, una persona de 17 años nacida a final de año pasaría el filtro `año ≤ actual−18` | B | A | Edad mínima **18** (equipo 17/11). Filtro por año + comprobación humana; para garantizarlo hará falta fecha completa (decisión futura) | Fundación | PENDIENTE (fuera de alcance PoC) |
| R13 | **Rectificación/supresión** de datos en versiones históricas | M | M | Procedimiento de derechos; respuestas congeladas con evento de rectificación; supresión con borrado de `answers` y `person` conservando `audit_event` sin datos personales | Fundación / DPO | PENDIENTE |
| R14 | **Datos reales introducidos por error** en el entorno de demo | M | A | `is_synthetic`, aviso `acepta_datos_sinteticos`, dominios reservados en demo | Equipo | MITIGADO PARCIALMENTE |

## 4. ¿Hace falta una EIPD?

**No se declara obligatoria.** Señales que justifican analizarla antes de tratar **datos reales** (art. 35): posible tratamiento de datos de categorías especiales (R4), colectivos en situación de vulnerabilidad, y uso del dato para valorar a personas. Lo hace la Fundación con su DPO usando la lista de tratamientos de la AEPD (art. 35.4) y el art. 35.3. **Con datos sintéticos no hay tratamiento de datos personales reales**, por lo que no se bloquea el desarrollo, pero sí la puesta en producción.

## 5. Requisitos jurídicos frente a recomendaciones

| Tipo | Elemento |
|---|---|
| **Requisito jurídico** (a verificar con DPO) | Base de licitud identificada (art. 6) y, para categorías especiales, condición del art. 9.2; información al interesado (art. 13); minimización y limitación de finalidad (art. 5); privacidad por defecto (art. 25); seguridad (art. 32); límites a decisiones automatizadas (art. 22) |
| **Recomendación de diseño** | Campos opcionales por defecto; `prefer_not_to_say`; sensibles solo en detalle y para personal de gestión; sensibles fuera de listados y logs; versiones de formulario inmutables; revisión humana de toda admisión; supresión de agregados pequeños |
| **Política del proyecto** | Solo datos sintéticos; RBAC por rol+ámbito; auditoría append-only |

## 6. Estado de las decisiones (17/11/2026)

| # | Tema | Estado |
|---|---|---|
| D1 | Responsable del tratamiento y base de licitud | **Pendiente**, anotado en `docs/producto/README.md`; fuera de alcance |
| D2 | ¿El financiador exige nacionalidad, país y género? | **Respondida por el equipo: sí**; ratificar con Melissa |
| D3 | Opciones de situación actual por financiador | **Simuladas en seed** para el MVP; la lista real la aporta la Fundación después |
| D4 | Plazos de conservación | **Pendiente**, fuera de alcance |
| D5 | Edad mínima | **18 años** (equipo) |
| D6 | Quién ve datos sensibles | **Respondida**: selección, preselección/captación y administración; no coder, alumno ni aspirante |
| D7 | EIPD | **Pendiente**, la valora la Fundación antes de usar datos reales |
| D8 | `motivacion` | Se mantiene la experiencia; `motivacion` queda opcional/heredada |
| D9 | Residencia: revisión o elegibilidad | **Depende de la convocatoria**; la confirma una persona; se pide siempre |
| D10 | Rectificación y borrado (por correo) | Proceso **pendiente**, fuera de alcance |
