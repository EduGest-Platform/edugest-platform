# KAN-107 · Entregable 3 — Evaluación de privacidad / Privacy assessment

## Acreditación documental KAN-49 (24/11/2026) / Documentary accreditation

ES: la matrícula añade estado/versión documental y el identificador/fecha de la persona administradora que acredita. Son metadatos operativos vinculados a la matrícula; no son nuevos campos del formulario, documentos, URLs ni categorías especiales. La proyección del alumno omite la identidad verificadora; el registro protegido y la auditoría conservan la atribución. Estado inicial pendiente, sin inferir revisiones históricas. Solo datos sintéticos; no acredita cumplimiento jurídico ni autoriza tratar documentos reales. Alcance, permisos y límites: [informe KAN-49](../reports/KAN-49-enrollment-documentation.md).

EN: enrollment adds documentary state/version and accrediting administrator ID/time. These are operational metadata linked to enrollment, not new form fields, document contents/URLs or special-category fields. Learner responses omit verifier identity; protected persistence/audit retain attribution. Initial pending status does not infer historical review. Synthetic data only; no legal-compliance claim or authorization for real documents. Scope and limits: [KAN-49 report](../reports/KAN-49-enrollment-documentation.md).

## Actualización técnica KAN-226 (24/11/2026) / Technical update

ES: `call.publication_state` (`draft`/`published`) y `call.publication_version` (entero >= 1) son metadatos editoriales de la oferta. No añaden datos personales, preguntas, consentimiento ni versión de formulario. La migración `0018` conserva la visibilidad de las ofertas ya públicas; las nuevas quedan en borrador por defecto. El filtrado de borradores en catálogo e inscripción se completa en los tramos dependientes del stack, no en el PR de modelo aislado. No acredita aceptación PO ni conformidad jurídica.

EN: `call.publication_state` (`draft`/`published`) and `call.publication_version` (integer >= 1) are offer editorial metadata. They add no personal data, questions, consent or form version. Migration `0018` preserves previously public offers; new rows default to draft. Draft filtering in catalogue and registration is completed by dependent stack increments, not the model PR alone. This is neither PO acceptance nor a legal compliance finding.

**Alcance:** el proyecto es una prueba de concepto gratuita con datos sintéticos. La validación legal (base jurídica, EIPD, plazos, responsable y DPO) **queda fuera del proyecto** y corresponde a la Fundación en una fase con datos reales; aquí solo se deja el diseño preparado. **Estado:** análisis técnico-funcional preliminar. **No sustituye al DPO ni al asesoramiento jurídico de la Fundación.** No declara que ningún tratamiento sea lícito, ilícito ni que la EIPD sea obligatoria.
> **EN summary:** Risk matrix for the application form. Nationality, birth country and gender are kept (PO decision 17/11/2026); this document records the risk, the alternative, and who must authorise. Disability is treated as a probable special-category (health) datum.

## 1. Fuentes y su uso

> **Verificación de la revisión V2 (17/11/2026):** se contrastaron referencias oficiales de RGPD en EUR-Lex y las guías de privacidad desde el diseño/por defecto de la AEPD, incluidas las recomendaciones de acceso según necesidad. **No hay validación de conformidad para una puesta en producción ni estudio jurídico particular de la Fundación.**

| Fuente | Referencia | Para qué se usa aquí | Tipo |
|---|---|---|---|
| [RGPD — Reglamento (UE) 2016/679 (EUR-Lex)](https://eur-lex.europa.eu/legal-content/ES/ALL/?uri=CELEX:32016R0679) | Arts. 4, 5, 6, 7, 9, 13, 15–17, 22, 25, 32 y 35 | Principios y obligaciones aplicables si se tratan datos personales reales | **Norma legal** |
| [LOPDGDD — Ley Orgánica 3/2018 (BOE)](https://www.boe.es/buscar/act.php?id=BOE-A-2018-16673) | Régimen complementario español y garantías | Debe ser revisada con asesoría responsable antes de tratar datos reales | **Norma legal; aplicación concreta pendiente** |
| [AEPD — privacidad desde el diseño](https://www.aepd.es/derechos-y-deberes/cumple-tus-deberes/medidas-de-cumplimiento/proteccion-de-datos-desde-el-diseno) y [Guía de Privacidad desde el Diseño](https://www.aepd.es/guias/guia-privacidad-desde-diseno.pdf) | Need-to-know, perfiles de acceso diferenciados y datos mínimos | Orientación de la autoridad, que fundamenta controles por grupo/ámbito | **Guías oficiales** |
| [AEPD — Guía de Protección de Datos por Defecto](https://www.aepd.es/guias/guia-proteccion-datos-por-defecto.pdf) | Privilegios mínimos y administración de roles por personas autorizadas | Base para gestión segura de concesiones y revocaciones | **Guía oficial** |
| Documentos del repositorio | `CONSTITUTION.md`, `AGENTS.md`, ADR-0003 | Reglas del proyecto (datos sintéticos, revisión humana, RBAC por ámbito) | Política interna |

## 2. Naturaleza de los datos

| Dato | Calificación preliminar | Razonamiento |
|---|---|---|
| Nombre, apellidos, correo, teléfono, año de nacimiento, provincia | Ordinario | Identificación/contacto; riesgo bajo-medio |
| Nacionalidad, país de nacimiento | Ordinario, **no categoría especial automáticamente**; riesgo de actuar como *proxy* de origen étnico/racial | Evaluar finalidad y contexto; puede facilitar discriminación indirecta |
| Género | Puede ser dato personal ordinario, con riesgos elevados según contexto y combinaciones; A no conserva opciones; B sí las captura; C describe otra lista todavía sin verificar | Obligatorio observado; B incluye "Prefiero no identificarme". No trasladar su lista a A/C sin confirmar. Sin cuotas ni scoring no autorizados |
| "Situación actual": discapacidad | **Probable dato relativo a la salud (art. 9)** | Requiere condición adicional del art. 9.2, **a determinar por DPO** |
| "Situación actual": inmigrante, refugiada/o, riesgo de exclusión, mujer en situación de vulnerabilidad, acceso limitado a recursos | **A evaluar**: pueden revelar condición socioeconómica o, según el caso, origen étnico/racial o convicciones; no se puede decidir sin análisis de contexto | Tratar con las mismas medidas que art. 9 por precaución (decisión de diseño, no afirmación jurídica) |
| Estado del certificado de discapacidad (C, sin verificar) | Dato de salud; protección G6 | Necesidad, obligatoriedad y condición de tratamiento real pendientes; no subida de documento propuesta |
| Entidad de derivación (C, sin verificar) | Posible proxy de situación vulnerable/salud; G6 por precaución | Fuente, finalidad y alcance pendientes PO/Fundación |
| Disponibilidad, experiencia, canal | Ordinario | — |

## 3. Matriz de riesgos

Probabilidad (P) e impacto (I): B/M/A. Estado: ABIERTO · MITIGADO EN DISEÑO · PENDIENTE DE DECISIÓN.

| ID | Riesgo | P | I | Mitigación propuesta | Quién autoriza | Estado |
|---|---|---|---|---|---|---|
| R1 | Recogida **excesiva** (campos sin finalidad acreditada: motivación, país de nacimiento, canal) | M | M | Cada campo con finalidad (Entregable 1 §2.3); `opcional` por defecto cuando no sea exigencia del financiador | PO + Fundación | PENDIENTE |
| R2 | **Base jurídica no confirmada** para el tratamiento; confusión entre "casilla" y consentimiento | A | A | No usar la casilla `#14` como base; registrar versión de aviso y fecha; determinar base con DPO. Consentimiento explícito solo donde proceda (p. ej. comunicaciones `#13`, y posible excepción art. 9.2.a para datos especiales) | Fundación / DPO | PENDIENTE |
| R3 | **Nacionalidad, país de nacimiento y género** observados en formulario; exigencia del financiador y uso para cuotas **no acreditados** | M | A | Mantener campos en diseño sintético por decisión PO, pero bloquear ranking/cuotas/prioridades hasta acreditar finalidad, base y proporcionalidad; acceso G3 según política PO 19/11 (admin/selección en ámbito; otros con concesión) | Fundación / DPO (antes de datos reales) | ABIERTO |
| R4 | **Discapacidad**, estado de certificado en C (salud) y otras opciones de `#11`; entidad de derivación C como posible proxy sensible, fuente C pendiente | M | A | Además del permiso de expediente, aplicar política G6 PO 19/11: admin/selección por defecto en ámbito; otros con concesión por persona/convocatoria; si una casilla es de categoría especial, proteger el grupo entero. Sin acceso en listados ni logs; art. 6 + condición art. 9.2 deben determinarse antes de usar datos reales | Fundación / DPO | ABIERTO; diseño preparado |
| R5 | **Decisión automatizada** sobre personas | B | A | Reglas de convocatoria (p. ej. residencia Madrid) solo *señalan* para revisión humana; admisión siempre humana (`pendiente_decision_humana`; art. 22) | PO | MITIGADO EN DISEÑO |
| R6 | **Exposición horizontal y vertical**: leer otra convocatoria o categoría sin habilitación | M | A | Rol activo + ámbito + política G3/G6 vigente (por defecto admin/selección; otros con concesión no caducada). Comprobarlo en FastAPI y filtrar en serialización, no solo en UI. Test 403/redacción, revocación inmediata y acceso cruzado | Backend / responsable funcional | ABIERTO; RBAC base ya existe, permiso granular **no** |
| R7 | **Datos sensibles en notas CRM** (`application_event.resumen` y `application_event.next_action`) | M | A | Aviso ya presente en `EventCreate.resumen` y `next_action.description`; propuesta: lista de comprobación y formación de usuarios; evaluación posterior de detección | Selección / DPO | ABIERTO |
| R11 | **Identidad por correo** (KAN-274): unir a dos personas que comparten correo, o revelar a un perfil sin ámbito que alguien solicitó otra convocatoria | M | A | Fichas separadas hasta decisión humana con autor, fecha y motivo; detalle solo con permiso CRM en todas las convocatorias implicadas; fuera de ámbito se avisa de que hay coincidencia, sin detalle; no se puede admitir con el aviso pendiente (el mensaje de admisión no dice cuál es la comprobación); tras decidir, el motivo mantiene la misma regla de alcance. Consecuencia aceptada al unir: el equipo de la convocatoria nueva ve el nombre del registro anterior. Sin deshacer en esta versión | Backend / PO | MITIGADO (pruebas en `test_identity_review.py`); deshacer una decisión: PENDIENTE |
| R8 | **Datos sensibles en logs** | B | A | KAN-105/#23 ya añade `app.access`, IDs de petición de servidor y errores seguros; #29 evita relanzar excepciones tras iniciar respuesta en `dev` `d59ee8c` (**CODE_PRESENT_NOT_RUN** aquí). Verificar todos los sinks, incluidos Uvicorn/proxy/CI; no registrar `answers`, G3/G6 ni mensajes de excepción; coordinar retención con KAN-209/#25 | Backend | MITIGADO EN DISEÑO (a verificar con test) |
| R9 | **Sin plazo de retención** definido | A | M | Fijar `[N meses]` con la Fundación; job de borrado/anonimización posterior | Fundación | PENDIENTE |
| R10 | **Estadísticas reidentificables** (grupos pequeños) | M | M | Supresión ya implementada: `min_group_size=5`, `min_cell_size=3` en `GET /calls/{id}/summary`; aplicar igual a cualquier agregado de datos sensibles | Backend | MITIGADO (código presente; test existente) |
| R11 | **Sesgo/discriminación indirecta** por nacionalidad, residencia, género o situaciones vulnerables | M | A | **No implementar cuotas ni prioridades** por esos datos hasta acreditar criterio legal, necesidad, no discriminación y aprobación de Fundación. Revisión humana necesaria, pero no suficiente para legitimarlos. Evaluar si se plantea IA | Fundación / DPO / PO | ABIERTO |
| R12 | **Edad por convocatoria**: A publica mayoría de edad, B **más de 16 años**; el año no prueba edad exacta para ninguno | B | A | Versionar años, operador y fecha de referencia aprobados; sin umbral global. Revisión humana con información suficiente y proporcionada, sin aceptación/rechazo automático; PO 19/11: fecha de inicio y B `gte` 16 para diseño sintético; condiciones reales pendientes Fundación | Fundación / PO | PENDIENTE |
| R13 | **Rectificación/supresión** con instantáneas y auditoría | M | M | Aplicar proceso autorizado de rectificación, supresión y límites de conservación. `audit_event` con IDs reidentificables sigue siendo **seudonimizado**, no anónimo; planificar retención/disociación conforme a finalidad y garantías | Fundación / DPO | PENDIENTE |
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
| D2 | ¿El financiador exige nacionalidad, país y género? | **OBSERVADO en bootcamp + DECISIÓN PO de mantener en demo**; **exigencia contractual no confirmada**. Solicitar fundamento a Melissa |
| D3 | Opciones de situación actual por financiador | **Simuladas en seed** para el MVP; la lista real la aporta la Fundación después |
| D4 | Plazos de conservación | **Pendiente**, fuera de alcance |
| D5 | Edad mínima | **PO 18/11:** edad configurable por convocatoria y mayoría de edad para bootcamp 1.250 h, aceptadas en diseño sintético. B publica >16. **PO 19/11:** edad al inicio del curso y «más de 16» = 16 o más; con solo el año, revisión humana |
| D6 | Quién ve datos sensibles | **PO 19/11:** administración y selección ven G3/G6 por defecto; administración concede o retira el acceso a otros perfiles, con auditoría. (Sustituye la propuesta anterior de que admin no tuviera lectura automática.) El aspirante tiene derechos de protección de datos, independientes del acceso a notas internas |
| D7 | EIPD | **Pendiente**, la valora la Fundación antes de usar datos reales |
| D8 | `motivacion` | **PO 18/11:** motivación inicial opcional en diseño, profundizada en entrevista. Sigue **obligatoria en API/BD** (`NOT NULL`) hasta implementar en KAN-42 |
| D9 | Residencia: revisión o elegibilidad | **PO 18/11:** obligatoria en bootcamp 1.250 h por requisito territorial publicado (Comunidad de Madrid); revisión humana. **PO 19/11:** en otras convocatorias, configurable según lo publicado, con revisión humana |
| D10 | Rectificación y borrado (por correo) | Proceso **pendiente**, fuera de alcance |

## 7. Privilegios dinámicos y riesgos adicionales (V2)

| ID | Riesgo | Control preventivo | Estado |
|---|---|---|---|
| R15 | Persona asigna acceso sensible a sí misma o excede su convocatoria | El operador solo gestiona concesiones si tiene `data_access.manage`; **prohibir auto-concesión**, exigir aprobación funcional y comprobar `call_id` | DISEÑO, NO IMPLEMENTADO |
| R16 | Acceso permanece activo después del cambio de rol, revocación o fecha fin | Comprobación de permiso por petición; `expires_at`, `revoked_at` y vigencia de rol; revocación inmediata, sin depender del frontend | DISEÑO, NO IMPLEMENTADO |
| R17 | Campos protegidos escapan por `Summary`, notas CRM, exportación o logs | DTO allowlist según categoría/ámbito; omisión por defecto; pruebas negativas en todas las rutas/exportaciones | DISEÑO, NO IMPLEMENTADO |
| R18 | Concesión sin justificación o auditoría de lectura | Registrar actor, destinatario, convocatoria, grupo, acción, fecha, motivo codificado y expiración; `audit_event` sin valores sensibles | DISEÑO, NO IMPLEMENTADO |

**Principio:** Administración y selección: acceso por defecto dentro del ámbito autorizado. Otros perfiles: permiso base más concesión G3/G6 vigente por usuario y convocatoria, concedida/revocada por administración y auditada. Solo detalle, nunca listas ni logs. Decisión PO 19/11; no implementada. Aprobación funcional y ejecución administrativa de concesiones adicionales; no auto-concesión. La Fundación define la autoridad y base para datos reales.

**EN:** Admin and selection have default access within their authorised scope. Other profiles need the base permission plus an active user/call/group grant managed by admin and audited. Detail only, never lists or logs. PO decision of 19 November; not implemented. Existing RBAC does not implement granular groups; human review is not legal validation.

## English edition (equivalent sections, KAN-107 V2)

**Scope.** Free proof of concept with synthetic data. Legal validation (lawful basis, DPIA, retention, controller, DPO) is outside the project and belongs to the Foundation before any real data. Official GDPR (EUR-Lex) and AEPD guidance were consulted on 17/11/2026; this is **not** a compliance validation.

**§2 Data nature.** Ordinary: name, email, phone, year of birth, province, availability, experience, channel. Nationality/country of birth: ordinary but a proxy risk for ethnic origin. Gender: risky depending on context; A options were not captured, B includes a captured list and "Prefiero no identificarme", C describes a different unverified list. Disability: probable health data (art. 9). Other "current situation" options: to be assessed case by case.

**Reconciled evidence (18/11).** Disability certificate status in unverified C is health data under G6; referring entity is also proposed G6 as a potential sensitive proxy, pending source, purpose and PO scope. Do not collect uploads by default. KAN-105/#23 logging is now present in `dev` `d59ee8c` (CODE_PRESENT_NOT_RUN here); verify all sinks and align retention with KAN-209/#25, now merged and refreshed after #23; current #29 also avoids re-raising post-response errors. Runtime checks remain pending.

**§3 Risk matrix and §4 DPIA.** Risks R1–R18 with preventive controls; whether a DPIA is needed is for the Foundation to assess before real data.

**§5 Legal requirements vs. recommendations vs. project policy.** Legal items (art. 5, 6, 9.2, 13, 22, 25, 32) must be verified with the DPO. Design recommendations: optional by default, `prefer_not_to_say`, sensitive data only in detail views, immutable form versions, human review of every admission. Project policy: synthetic data only, RBAC by role and scope, append-only audit. Human review alone is not a lawful basis for selection criteria.

**§6 Decisions.** D1/D2/D4/D7 remain Foundation matters for real data. PO 19 November resolved D5 age at course start (B at least 16), D6 admin/selection default scoped G3/G6 access with admin-managed additional grants, D9 configured residence. Initial motivation/availability optional in design, still required by current API/DB. Form C outside MVP.

**§7 Dynamic privileges (R15–R18).** Self-grant, stale access after revocation, leakage through summaries/CRM/exports/logs, and ungrounded grants are mitigated by design (not implemented): `data_access.manage`, no self-grant, per-request checks, DTO allow-lists and audit without values.
