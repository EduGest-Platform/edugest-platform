# Decisiones PO 19/11/2026: acceso, invitaciones, tablero y comunicaciones / PO decisions: access, invitations, board and communications

**Estado / Status:** decisiones de la Product Owner (Elizabeth) del 19/11/2026. **No implementadas** salvo donde se indica. **Discrepancia abierta:** la PO indica que Melissa confirmó el 19/11/2026 el envío automático de correos de estado, pero la revisión del Drive (consolidación del 19/11) no encontró esa respuesta: el documento «Preguntas para Melissa: Ronda 3» del 19/11 solo contiene la propuesta. Hasta adjuntar la respuesta, tratar D6 como decisión PO pendiente de evidencia de Melissa. / PO decisions, not implemented unless stated.

## 1. Decisiones / Decisions

| # | Tema | Decisión |
|---|---|---|
| D1 | Aspirante | **No tiene rol ni acceso a la plataforma.** Registra su interés en el formulario público y se crea automáticamente su perfil en el CRM. No recibe invitación |
| D2 | Coder (alumnado) | Rol con acceso. **El equipo lo invita por correo al matricularlo** (tras la admisión) |
| D3 | Personal | Administración, coordinación, captación, selección y docente **entran por invitación de administración** (administración puede cambiar quién invita) |
| D4 | Administración | Corresponde a **dirección general**. Tiene un **panel para dar, modificar y quitar permisos** |
| D5 | Coordinación | **Mismas funciones que administración, sin poder añadir usuarios** |
| D6 | Correos de estado | El equipo podrá enviar **correos automáticos sobre cómo va la candidatura** (según la PO, confirmado por Melissa el 19/11/2026; **sin evidencia en el Drive**, ver Estado) |
| D7 | Código de candidatura | **Numérico: año + número**, por ejemplo `2027-00123`, único en la plataforma |
| D8 | Tablero de coordinación | Tablero común tipo Trello con columnas: **1 Aspirantes · 2 Entrevistados · 3 Admitidos · 4 Lista de espera · 5 Tal vez** (ultimando detalles, p. ej. falta documentación) **· 6 Esta vez no · 7 Recomendaciones** (no admitidos con derivación a otro recurso) |
| D9 | Columnas y etapas | Las columnas son **etapas reales** de la candidatura, pero **el equipo podrá modificar el tablero**. **Pendiente:** qué movimientos se automatizan y cuáles exigen decisión humana |
| D10 | Etiquetas y comentarios | El equipo puede **etiquetar** a las personas y dejar **comentarios visibles para el resto** del equipo |
| D11 | CRM | El personal de la fundación usa el CRM y **registra correos y llamadas** (seguimiento) |
| D12 | Admisión | Por defecto la deciden **selección y coordinación**; **todo será configurable** (quién tiene cada permiso) |

## 2. Qué existe hoy y qué cambia / What exists and what changes

| Decisión | Hoy en `dev` | Cambio necesario |
|---|---|---|
| D1 | La cuenta sintética `aspirante-01` puede iniciar sesión y ver `GET /me/applications`; la interfaz muestra «aspirante» como si fuera un rol | Quitar el acceso del aspirante: solo formulario público. Revisar seed, `/me/applications`, menús y E2E |
| D2, D3 | No hay invitaciones; cuentas creadas por el seed | Invitaciones con caducidad, reenvío y revocación (KAN-38, KAN-223, KAN-225, KAN-222) |
| D4, D5 | No hay panel; permisos por asignación en base de datos. Coordinación solo ve agregados y excepciones | Panel de permisos (KAN-36, KAN-257). Ampliar coordinación a las funciones de administración salvo alta de usuarios: **cambio grande de permisos** que conviene probar como la matriz RBAC |
| D6 | Envíos simulados de recordatorios en revisión (PR #57, KAN-129) | Plantillas de estado; en la demo, bandeja simulada sin envío real. «Esta vez no» con revisión humana antes de enviar (KAN-50) |
| D7 | Código `IA27A-0001` (prefijo por convocatoria) | Nuevo formato y migración; mantener el antiguo como referencia si ya existe |
| D8, D9 | Etapas: `enviada`, `requisitos_en_revision`, `convocada`, `evaluacion_en_curso`, `pendiente_decision_humana`, `admitida`, `lista_espera`, `no_admitida`, `retirada` | Mapear columnas a etapas (ver §3); añadir las que falten (p. ej. «Tal vez», «Recomendaciones») |
| D10 | No hay comentarios ni etiquetas | Comentarios (KAN-51, KAN-228, KAN-235). Etiquetas: **sin tarea** |
| D11 | CRM con contactos y resultado del contacto (KAN-153) | Seguimiento de correos y llamadas con próximo paso (KAN-45, KAN-127) |
| D12 | Decisión de admisión sin implementar | Decisión conjunta configurable (KAN-48, KAN-147, KAN-175) |

## 3. Propuesta de mapeo columnas → etapas / Proposed column → stage mapping

| Columna | Etapa propuesta | ¿Cómo se entra? (propuesta, pendiente D9) |
|---|---|---|
| 1 Aspirantes | `enviada`, `requisitos_en_revision` | Automático al inscribirse |
| 2 Entrevistados | `convocada`, `evaluacion_en_curso` | Persona del equipo |
| 3 Admitidos | `admitida` | **Solo con decisión humana registrada** (motivo y firmantes, KAN-48) |
| 4 Lista de espera | `lista_espera` | Decisión humana registrada |
| 5 Tal vez | nueva: `pendiente_documentacion` (o etiqueta sobre `pendiente_decision_humana`) | Persona del equipo |
| 6 Esta vez no | `no_admitida` | **Solo con decisión humana registrada**; comunicación revisada (KAN-50) |
| 7 Recomendaciones | `no_admitida` + derivación registrada (o etapa propia) | Persona del equipo, con el recurso recomendado |

## 4. Criterios para una plataforma real / Real-platform criteria

- **Un solo modelo de estados con varias vistas**: tablero y expediente leen y escriben lo mismo; nunca se contradicen.
- **Etiquetas en lista cerrada** gestionada por administración; nunca datos sensibles (G3/G6).
- **Comentarios** con autor, fecha, edición y resuelto, visibles solo dentro del ámbito.
- **Invitaciones** que caducan (propuesta: 7 días), se reenvían o revocan; roles altos con aprobación; todo cambio de permisos auditado; revisión periódica de accesos.
- **Correos automáticos** con plantillas revisadas; en la demo, simulados; las malas noticias, revisadas por una persona antes de enviarse y con vía para pedir revisión humana (RGPD art. 22).

## 4b. Contraste con el Drive (consolidación del 19/11) / Drive cross-check

- Siete perfiles: confirmados por Somos F5 (30/10); la matriz detallada de permisos no está validada por Melissa.
- Dirección general como rol separado: no encontrado. Inscripción sin cuenta y con código de referencia: descrita como punto de partida (Ronda 3).
- Columnas, etiquetas y quién mueve las tarjetas: no encontrados como decisión de Melissa; el tablero es propuesta del equipo (backlog 12/11). `tal_vez` y `esta_vez_no` son decisión PO del 11/11.
- Formato del código de candidatura: no encontrado. Quórum de dos firmas: propuesta (Ronda 3), no confirmado.
- Requisitos en paralelo, lista de espera abierta y entrevista individual alternativa: confirmados por Melissa el 06/11.

## 5. Propuesta de alcance hasta el 04/12 / Scope proposal to 04/12

**MVP:** tablero con columnas mapeadas a etapas, comentarios y etiquetas, invitaciones de personal y coder, panel de permisos básico, correos de estado simulados, quitar acceso al aspirante, código numérico.
**Después:** menciones, revisión periódica de accesos, permisos totalmente configurables, envío real de correos.

## English summary

Applicants have no role or platform access: the public form creates their CRM profile. Learners (coders) and all staff join by invitation (staff invited by admin, coders by the team at enrolment). Admin is general management with a permissions panel; coordination gets the same features except adding users. Automatic application-status emails are a PO decision; the PO reports Melissa confirmed them on 19/11, but the Drive review found no written answer yet. Application codes become year + number (e.g. `2027-00123`). A shared coordination board has seven columns mapped to real stages, editable by the team; which moves are automated and which require a human decision is pending. Tags and team-visible comments, CRM tracking of emails and calls, and admission decided by selection and coordination by default, all configurable. Proposed MVP and later items are listed above.
