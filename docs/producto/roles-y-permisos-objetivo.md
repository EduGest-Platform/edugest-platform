# Roles y permisos objetivo / Target roles and permissions

**Estado / Status:** modelo **objetivo** acordado por la Product Owner (Elizabeth) el 19/11/2026, para orientar el diseño. **No es el estado actual del código**: lo implementado hoy está en [funcionalidades-por-rol.md](funcionalidades-por-rol.md) y las decisiones, con su contraste con el Drive, en [decisiones-po-2026-11-19-acceso-tablero.md](decisiones-po-2026-11-19-acceso-tablero.md). Las celdas marcadas como propuesta no están validadas por la fundación. / Target model, not the current code.

**Idea central / Core idea:** casi todo será **configurable** desde el panel de administración. La tabla muestra el valor **por defecto** de cada rol; administración podrá activarlo o quitarlo. Solo unas pocas reglas son **fijas** y no se pueden cambiar desde el panel (§3). / Almost everything is configurable; the table shows defaults; a few rules are fixed.

## Leyenda / Legend

| Símbolo | Significado |
|---|---|
| ✅ | Permitido **por defecto** (configurable: administración puede quitarlo) |
| ⚙️ | **No** por defecto, pero administración puede **activarlo** |
| 👤 | Solo sobre **lo propio** (su candidatura, su matrícula, sus entregas) |
| 🔒 | **Nunca**: regla fija, no configurable |
| — | No aplica |

Todos los permisos del personal se conceden **por ámbito** (programa, convocatoria o cohorte) y se comprueban en el servidor. / Staff permissions are always scoped and enforced server-side.

## 1. Perfiles / Profiles

| Perfil | Quién es | Cómo entra |
|---|---|---|
| **Administración** | Dirección general | Invitación (la primera cuenta se crea en la instalación) |
| **Coordinación** | Coordinación de programas y cohortes | Invitación de administración |
| **Captación** | Personal de la fundación que capta y hace seguimiento | Invitación de administración |
| **Selección** | Colaboradores del proceso de selección | Invitación de administración |
| **Docente** | Profesorado de una cohorte | Invitación de administración |
| **Coder** | Alumnado matriculado | Invitación del equipo **al matricularse** tras la admisión |
| **Aspirante** | Persona interesada (estado de `Person`, no rol de personal) | Formulario público (también sin sesión); con cuenta, ve **solo sus propias candidaturas**. Decisión PO 20/11: se mantiene |

## 2. Funciones por rol (valores por defecto) / Features by role (defaults)

| Área | Función | Admin. | Coord. | Captación | Selección | Docente | Coder | Aspirante |
|---|---|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| **Usuarios y permisos** | Invitar personal (crear usuarios) | ✅ | 🔒 | ⚙️ | ⚙️ | ⚙️ | — | — |
| | Dar, modificar y quitar permisos (panel) | ✅ | ✅ ¹ | ⚙️ | ⚙️ | ⚙️ | — | — |
| | Invitar a coders al matricularlos | ✅ | ✅ | ⚙️ | ✅ | ⚙️ | — | — |
| | Consultar el registro de auditoría | ✅ | ✅ | ⚙️ | ⚙️ | ⚙️ | — | — |
| **Configuración** | Programas, convocatorias, cohortes y requisitos | ✅ | ✅ | ⚙️ | ⚙️ | ⚙️ | — | — |
| | Plantillas de correo y reglas de automatización | ✅ | ✅ | ⚙️ | ⚙️ | — | — | — |
| | Política de silencio de una convocatoria | ✅ | ✅ | ✅ | ⚙️ | — | — | — |
| **Inscripción y CRM** | Inscribirse en el formulario público | — | — | — | — | — | — | ✅ |
| | Ver mis propias candidaturas (sin notas internas) | — | — | — | — | — | 👤 | 👤 |
| | Ver y editar fichas y expedientes | ✅ | ✅ | ✅ | ✅ | ⚙️ | — | 🔒 |
| | Registrar correos, llamadas, resultado y próximo paso | ✅ | ✅ | ✅ | ✅ | ⚙️ | — | — |
| | Revisar requisitos (cumple / no cumple) | ✅ | ✅ | ✅ | ✅ | ⚙️ | — | — |
| | Registrar excepciones de requisitos | ✅ | ✅ | ✅ | ✅ | ✅ | — | — |
| | Cerrar la preselección y revisar alertas de silencio | ✅ | ✅ | ✅ | ✅ | ✅ | — | — |
| **Tablero de coordinación** | Ver el tablero común | ✅ | ✅ | ✅ | ✅ | ⚙️ | — | — |
| | Mover tarjetas entre columnas sin decisión (Aspirantes, Entrevistados, Tal vez, Recomendaciones) ² | ✅ | ✅ | ✅ | ✅ | ⚙️ | — | — |
| | Etiquetar personas (lista cerrada) y comentar | ✅ | ✅ | ✅ | ✅ | ⚙️ | — | — |
| | Gestionar el catálogo de etiquetas | ✅ | ✅ | ⚙️ | ⚙️ | — | — | — |
| **Selección y admisión** | Registrar entrevistas y valoraciones | ✅ | ✅ | ⚙️ | ✅ | ⚙️ | — | — |
| | Decidir y firmar la admisión (Admitidos, Lista de espera, Esta vez no) ³ | ⚙️ | ✅ | ⚙️ | ✅ | ⚙️ | — | — |
| | Enviar correos de estado de la candidatura | ✅ auto ⁴ | ✅ | ✅ | ✅ | — | — | — |
| | Ver datos protegidos G3/G6 (origen, género, situación, discapacidad) | ✅ | ⚙️ | ⚙️ | ✅ | ⚙️ | — | — |
| **Formación** | Registrar asistencia | ✅ | ⚙️ | — | — | ✅ cohorte | — | — |
| | Corregir asistencia (con motivo) | ✅ | ✅ | — | — | ✅ cohorte | — | — |
| | Consultar asistencia | ✅ | ✅ | — | — | ✅ cohorte | 👤 | — |
| | Actividades, entregas, competencias y rúbricas | ⚙️ | ✅ consulta | — | — | ✅ cohorte | 👤 | — |
| | Feedback asistido por IA (borrador) | — | — | — | — | ✅ aprueba | 👤 lee lo aprobado | — |
| | Alertas de riesgo de abandono | ✅ | ✅ | — | — | ✅ cohorte | — | — |
| | Baja de matrícula (con motivo) | ✅ | ✅ | — | — | ⚙️ | — | — |
| **Asistente** | Preguntas sobre documentos y datos autorizados | ✅ | ✅ | ⚙️ | ⚙️ | ✅ | ✅ | — |
| **Indicadores** | Panel y agregados por convocatoria y cohorte | ✅ | ✅ | ✅ | ✅ | ⚙️ | — | — |

**Notas:**
1. Coordinación tiene las mismas funciones que administración **salvo crear usuarios** (decisión PO 19/11). Nadie puede concederse a sí mismo un permiso ni dar uno que no tiene (regla fija, §3). Conviene confirmar si coordinación puede modificar permisos de otros perfiles o solo solicitarlo, como proponía el diseño del 10/11.
2. **Pendiente de decidir** qué movimientos del tablero se automatizan y cuáles exigen decisión humana. Las columnas son etapas reales de la candidatura y el equipo podrá modificar el tablero.
3. La admisión la deciden **selección y coordinación por defecto** (decisión PO 19/11); el número de firmas (propuesta: dos personas distintas) no está confirmado por la fundación.
4. Los correos de estado se envían automáticamente según las plantillas; los de **«Esta vez no» los revisa una persona antes de enviarse**. En la demo no se envía nada real. Falta la confirmación escrita de Melissa (ver el documento de decisiones).

## 3. Reglas fijas (no configurables) / Fixed rules

| Regla | Por qué |
|---|---|
| Ninguna decisión de admisión, exclusión, no admisión o baja es automática | Constitución y AGENTS.md: decisión humana siempre |
| Nadie se concede permisos a sí mismo ni concede lo que no tiene | Evitar la escalada de privilegios |
| Coordinación no crea usuarios | Decisión PO 19/11 |
| El aspirante solo ve sus propias candidaturas; nunca expedientes ajenos, CRM ni notas internas | Decisión PO 20/11 (revierte D1 del 19/11) |
| El coder solo ve lo suyo | Privacidad del alumnado |
| Todo cambio de permisos, decisión, corrección y acceso denegado queda auditado, sin datos personales | Trazabilidad |
| El asistente no ejecuta SQL ni elige su ámbito | AGENTS.md §5 |
| En desarrollo, solo datos sintéticos y ningún envío real | Constitución |

## 4. Cómo se hará configurable / How it becomes configurable

- Los permisos ya viven en una sola tabla del servidor (`ROLE_PERMISSIONS` + asignaciones por ámbito). El panel de administración (KAN-36, KAN-257) editará esas asignaciones, con aprobación para roles altos, caducidad de invitaciones y revisión periódica de accesos.
- Cada cambio se audita y se puede revertir. Los valores de esta tabla serán los que traiga una instalación nueva.

## English summary

Target model agreed by the PO on 19/11/2026, not the current code. Administration is general management; coordination has the same features except creating users; captación, selección and docente work within their scopes; coders join by invitation at enrolment and see only their own data; applicants keep an account limited to their own applications (the public form creates their CRM profile; PO decision of 20/11 reverting D1). The table lists each role's default; almost everything is configurable by administration, except fixed rules: no automated admission or exclusion decisions, no self-granted or unheld permissions, coordination never creates users, applicants never see other people's data or internal notes, learners see only their own data, everything is audited, synthetic data only. Pending: board automation rules, the number of admission signatures, and Melissa's written confirmation of status emails.
