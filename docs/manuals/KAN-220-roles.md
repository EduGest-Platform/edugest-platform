# KAN-220 — Role operator manuals / Manuales operativos por rol

**Snapshot / Instantánea:** 23/11/2026, `dev@7f834ef`. **Owner / Responsable Jira actual:** Yohanna. **Reviewer / Revisor solicitado:** Anas. **Deadline:** 03/12/2026. The description retains an older David proposal; current assignee is Yohanna / la descripción conserva una propuesta antigua de David, pero el assignee actual es Yohanna.

## ES — Antes de operar

Esta guía describe las pantallas y límites presentes en código. No es evidencia de un ensayo completo ni aceptación de release. Usar cuentas y datos sintéticos del entorno autorizado; la contraseña se obtiene de su responsable, nunca de este manual. La inscripción pública no crea automáticamente una cuenta de usuario.

Comprobar el origen antes de interpretar resultados:

| Modo/pantalla | Origen y alcance |
|---|---|
| Sin URL API configurada en build | Todo es demo local; cambios en navegador no prueban persistencia PostgreSQL |
| Inscripción, Mi candidatura, Candidaturas y Auditoría en modo API | Son las cuatro vistas registradas para datos de servidor; su presencia en cada menú depende del rol |
| Calendario, Rúbricas, Alumnado, Asistencia, Entregas, Progreso, Tutoría y asistente | Siguen siendo vistas locales en esta instantánea; el aviso de origen local no se debe ignorar |

Referencia de esta separación: [configuración de origen](../../src/shared/api/config.ts) y [registro de pantallas](../../src/gistar/apiScreens.ts). Que exista una API académica no conecta automáticamente esas pantallas al servidor.

### Acceso y salida

1. En modo API, iniciar sesión con la cuenta asignada. Los roles disponibles provienen del servidor; el selector de rol no concede permisos.
2. El inicio/menú puede contener vistas locales. Buscar el indicador de origen antes de introducir o presentar datos.
3. Un 401 obliga a iniciar sesión de nuevo; 403 significa falta de permiso/ámbito, no expediente vacío. No cambiar al modo demo para aparentar haber completado la operación.
4. Cerrar sesión al terminar; no compartir tokens, contraseñas ni perfiles del navegador.

## ES — Administración

- El menú admin actual incluye **Auditoría**. Abrirla y actualizar para consultar acciones/identificadores del servidor. No es un editor ni una exportación completa del historial.
- Un ID o rol puede identificar indirectamente a una persona: no tratar auditoría como información anónima ni publicar su metadata libremente.
- No se incluye una pantalla para asignar roles, crear cuentas, borrar auditoría o configurar permisos. Solicitar esos cambios al responsable del backend mediante el proceso del equipo.
- En modo servidor el menú admin muestra también **Candidaturas** (KAN-275), con los expedientes y el alta manual; el menú de la demo local no la incluye.

## ES — Captación y selección

1. Con un rol de interfaz que incluya **Candidaturas**, abrir el listado del servidor. Captación se presenta como **Personal fundación**; selección tiene su menú propio. Los ámbitos los decide la API.
2. Buscar por nombre/correo/código sintético y usar los filtros de convocatoria/estado presentes. Abrir la fila correcta y comprobar código/convocatoria antes de actuar. No documentar aquí el filtro por actor del PR #115 mientras no esté integrado.
3. En **Historial CRM**, elegir Contacto/Nota/Recordatorio y canal cuando proceda; escribir solo un resumen operativo. Pulsar **Registrar en el historial** y comprobar la entrada recibida del servidor. Un recordatorio CRM no demuestra envío de correo.
4. En requisitos, elegir explícitamente una versión para consultar el estado y usar **Actualizar requisitos** si hay evidencia nueva. Este panel es de consulta; elegir versión no activa requisitos ni decide elegibilidad/admisión.
5. Para alertas de silencio, seleccionar una convocatoria y actualizar. La lista abarca toda esa convocatoria, no los filtros de texto/estado del listado. **Abrir expediente** lleva a su historial. El aviso no retira ni admite automáticamente a nadie.
6. El formulario CRM no implementa una decisión de selección, quórum ni matrícula. Los endpoints de decisión existentes son un flujo backend distinto; no sustituirlos por una nota que diga «admitida».

Selección (en **Candidaturas**) y Coordinación (en su **Inicio**) pueden registrar candidaturas a mano (KAN-275); eso no da acceso a los expedientes. Administración las registra en **Candidaturas**, que su menú muestra solo en modo servidor. Coordinación y docencia pueden tener capacidades de API específicas, pero no heredan automáticamente `applications.read` ni el menú de captación. Si falta una pantalla o devuelve 403, solicitar revisión de rol/ámbito; no usar otra identidad prestada.

## ES — Docencia

Las pantallas de alumnado, asistencia, entregas, rúbricas y competencias siguen locales. No usarlas para demostrar registros académicos persistidos ni el asistente conectado. La API de asistencia/competencias existente exige rol y cohorte asignados; su operación e integración requieren el flujo autorizado del backend y validación aparte.

El menú docente puede mostrar **Candidaturas**, pero su visibilidad no concede permiso backend. Si devuelve 403, detener la operación y solicitar autorización; no afirmar que la docencia ve todos los expedientes. No registrar evaluaciones reales en fixtures locales ni publicar feedback generado sin revisión humana.

## ES — Aspirante y coder

### Aspirante

1. Desde la opción pública de inscripción o **Inscripción**, elegir una convocatoria abierta, introducir datos sintéticos y aceptar el aviso del entorno sintético. Si hay error al cargar convocatorias, usar el reintento; no inventar una convocatoria.
2. Enviar una sola vez y esperar recibo o error. El recibo confirma la candidatura, no una admisión ni una nueva cuenta de acceso. Un duplicado no equivale a otra candidatura nueva.
3. **Mi candidatura** muestra las candidaturas de la Person vinculada a la sesión, sin notas internas. No asumir que registrar un email crea una sesión o vincula cualquier cuenta posterior.

### Coder

El rol de experiencia coder se deriva de las matrículas de la cuenta. Su menú actual incluye progreso/entregas/asistente locales; no ofrece por sí solo una vista académica de servidor ni garantiza autoservicio de asistencia. Tampoco incluye automáticamente **Mi candidatura**: depende de los roles de interfaz disponibles. No usar un valor de demo como informe académico oficial.

## ES — Incidencias y evidencia mínima

| Situación | Acción |
|---|---|
| Catálogo vacío | Diferenciar «sin convocatorias abiertas» de error/cargando; reintentar solo cuando corresponda |
| API no disponible | Conservar el error y comprobar servicio/conexión; no declarar éxito por datos de demo |
| Escritura rechazada | Anotar fecha, operación y request_id si se muestra, sin reenviar cuerpos ni credenciales |
| Duda sobre ámbito | Confirmar cuenta, rol y convocatoria/cohorte con el responsable |
| Evidencia para revisión | SHA, modo de datos, pasos, resultado esperado/observado y datos sintéticos; evitar tokens/logs crudos |

No borrar volúmenes ni resetear seed para resolver un permiso. Esta guía no aprueba políticas de retención ni despliegues.

## EN — Data mode, access and role procedures

This is a source-checked operator guide, not a completed rehearsal or release acceptance. Use authorized synthetic accounts/data. Obtain credentials from the environment owner, never from this manual. Public registration does not create a login account.

Without a build-time API URL, every screen is local demo. In API mode only inscription, own applications, staff applications/CRM and audit use the server registry. Other academic/calendar/assistant screens remain local; backend academic endpoints do not automatically connect them. Check origin indicators before presenting or editing data. Server-derived roles determine allowed UI roles; a selector never grants authority. Reauthenticate after 401 and seek scope review after 403. Do not replace a failed server operation with a demo result; sign out when finished.

### Administration

The admin menu exposes **Auditoría**, a read-only recent server-action view, not a complete export/editor. IDs/roles may identify people. No role-grant, account-creation, audit-deletion or permission-management screen is provided here. In server mode the admin menu also shows **Candidaturas** (KAN-275); the local demo menu does not.

### Recruitment and selection

Open **Candidaturas** using an assigned UI role that includes it; recruitment maps to **Personal fundación**. Confirm the synthetic dossier and call before writing. Use the integrated search/call/stage controls; actor filtering in pending #115 is not documented as integrated.

Choose a CRM Contact/Note/Reminder and channel, enter minimal operational text, then **Registrar en el historial** and confirm the returned server event. A CRM reminder is not an email receipt. Requirement consultation requires explicit version selection; **Actualizar requisitos** refreshes evidence but does not activate policy or decide admission. Silence alerts require a selected call and manual refresh; their list covers the whole call independently of application text/stage filters. **Abrir expediente** opens the dossier; warnings do not automatically withdraw or admit anyone.

Selection (under **Candidaturas**) and coordination (on its **Home** screen) can register applications that arrive outside the public form (KAN-275), choosing the origin channel; this grants no dossier access. Administration does it under **Candidaturas**, which its menu shows in server mode only.

CRM is not the backend selection/quorum/enrollment workflow: a note saying “admitted” is not an admission decision. Coordinator/teacher API capabilities do not automatically include general application reads or recruitment UI access. Request proper scope instead of borrowing identities.

### Teaching

Learner, attendance, submission, rubric and competency screens remain local demo on this snapshot. They do not demonstrate PostgreSQL writes or a connected assistant. Academic APIs require assigned role/cohort and separate authorized integration. The teacher menu can display **Candidaturas** while the backend still denies access; visibility is not permission. Stop on 403. Do not record real evaluations in demo fixtures or publish unreviewed generated feedback.

### Aspirant and coder

Aspirants use public registration or **Inscripción**, choose an actual open call, enter synthetic data and accept the synthetic-environment notice. Retry a failed catalogue load instead of fabricating a call. Submit once; a receipt proves intake, not admission or account creation. **Mi candidatura** is limited to the Person attached to the authenticated account and exposes no internal notes. Email submission alone does not establish account linkage/session ownership.

Coder experience derives from account enrollments. Its progress/submission/assistant screens are local and do not guarantee server academic self-service; its menu does not automatically include **Mi candidatura**. Never present local values as official academic evidence.

### Incidents and evidence

Distinguish empty catalogue from loading/error, and unavailable API from valid demo fixtures. Record date, commit, data mode, minimal steps and expected/observed result; include a displayed request ID where useful, without tokens, credentials or raw bodies/logs. Confirm account and call/cohort scope with the owner. A permission error is not a reason to reset seed or delete volumes. No retention/deployment acceptance is implied.

## Sources and validation / Fuentes y validación

- [Shell](../../src/gistar/Shell.tsx), [menus](../../src/gistar/config.ts), [server session roles](../../src/shared/api/session.tsx).
- [API views](../../src/gistar/views/api/ApiAdmissions.tsx), [requirement panel](../../src/gistar/views/api/ServerRequirementReview.tsx), [silence panel](../../src/gistar/views/api/ServerSilenceReview.tsx).
- [Backend permissions](../../api/app/core/authz.py), [own applications](../../api/app/modules/admissions/router.py).

Static source/link/diff checks and the focused data-source registry tests are local evidence only. No new manual browser rehearsal, database writes or deployment was performed; CI completion is not inspected per user request. / Verificación local de fuentes/enlaces y registro de origen; no ensayo nuevo, escrituras ni despliegue, sin esperar CI.
