# Discussion API boundaries / Límites de la API de comentarios

## ES

Cadena KAN-233/KAN-244: #150 → #151 → #152 → #153 → PR de pruebas de seguridad. Implementación: Yohanna; revisión solicitada: Anas. Estado del flujo PostgreSQL: **CODE_PRESENT_NOT_RUN localmente**. No implica aceptación PO ni cierre de Jira.

### Permisos y ámbito

- Consultar exige el permiso existente `applications.read`; escribir exige `applications.crm`, siempre con ámbito del expediente o programa.
- Un permiso de convocatoria no habilita todos los hilos de su programa. Docencia, coordinación y personas sin esos permisos CRM no obtienen acceso por utilizar estas rutas.
- La autoría se deriva de la sesión. Editar/borrar un comentario o resolver/reabrir un hilo exige autoría o un wildcard administrativo existente que cubra el mismo ámbito. No se añaden asignaciones de rol.
- Los comentarios no son decisiones, no cambian etapas ni crean matrículas. No se envían notificaciones ni menciones externas.

### Contrato de uso

Todas las rutas tienen prefijo `/api/v1`. Ver OpenAPI para los campos completos.

| Método y ruta | Operación |
|---|---|
| `POST /discussion-threads` | Crear con `scope_type`, un único `application_id`/`program_id` y `subject`. |
| `GET /discussion-threads` | Filtrar por un ámbito exacto; `limit` 1–200 y `offset` ≥0. |
| `GET /discussion-threads/{id}` | Obtener versión y estado de resolución actuales. |
| `POST /discussion-threads/{id}/comments` | Crear raíz o respuesta con `body` y `parent_id` opcional del mismo hilo. |
| `GET /discussion-threads/{id}/comments` | Listado paginado plano, con referencias al padre. |
| `PATCH /discussion-comments/{id}` | `body` y `expected_version` del comentario observado. |
| `DELETE /discussion-comments/{id}` | JSON con `expected_version`; borrado lógico, sin borrar respuestas. |
| `POST /discussion-threads/{id}/resolution` | `resolved` y `expected_version` del hilo observado. |

Cada escritura de comentario incrementa su versión y la del hilo. Para resolver tras una respuesta/edición, volver a leer la versión del hilo. Un 409 exige recargar y revisar; no sustituir automáticamente la versión por la nueva para repetir una edición vieja. Un hilo resuelto debe reabrirse antes de modificar comentarios. La resolución repetida con la misma versión actual y el mismo estado no produce otra mutación.

El texto se conserva como texto, no se renderiza como HTML. La futura UI debe escaparlo y evitar `dangerouslySetInnerHTML`. Las pruebas API comprueban JSON/nosniff y ausencia de texto libre en metadatos de auditoría; no certifican un renderer que todavía no existe.

El borrado lógico conserva texto en la base para gestión interna, pero devuelve `body: null` en el contrato. No es borrado físico ni una política de retención aprobada. La auditoría conserva actor, acción, IDs y versiones; no copia cuerpo ni asunto. Las escrituras y su auditoría comparten transacción. El bloqueo sigue hilo → comentario para serializar cambios y rechazar versiones antiguas.

### Verificación y límites

Los contratos, permisos aislados, rutas anónimas, ocultación de texto borrado y versiones tienen pruebas locales sin conexión a PostgreSQL. Las pruebas de persistencia, rollback tras `flush`, ámbito y concurrencia requieren PostgreSQL. Docker no estaba disponible localmente; no se declara ese recorrido ejecutado. Esta API no incorpora UI, tiempo real, recuperación de contenido ni nuevas políticas de acceso para perfiles académicos.

## EN

This stack implements internal discussion APIs using existing application read/CRM authority. It does not grant new roles or broaden call-level authority into program-wide access. Authors or an existing matching administrative wildcard may edit/delete comments or resolve/reopen threads. Other authorized writers can reply but cannot modify somebody else's content. No discussion operation changes an admission or enrollment.

Use `/api/v1` plus the routes above. Thread creation takes exactly one scope target. Comments can reference an available parent in the same thread. Listing is bounded to 1–200 rows with nonnegative offsets. Edits and logical deletion require the observed comment version; resolution takes the observed thread version. Comment writes also increment the thread version. Refresh and review after 409; never blindly replay an old edit against a newly substituted version. Resolved threads must be explicitly reopened before comment mutations. An unchanged resolution request at the current version is a no-op.

Bodies are JSON/plain text, not trusted HTML. A future renderer must escape them; API JSON/nosniff tests are not an end-to-end XSS certification. Tombstones return null bodies while retaining stored text and existing replies. Logical deletion does not establish physical-erasure or retention policy. Audit holds actor/action/IDs/versions without free text; it commits atomically with the mutation. Thread-first, comment-second locking serializes edits and stale-version rejection.

Local tests cover contracts, isolated permissions, anonymous HTTP dispatch, tombstones and versions. PostgreSQL integration tests cover scope, rollback after flush and concurrent edits, but were not run locally because Docker was unavailable. No UI, real-time collaboration, external notification or academic-role access policy is delivered. Human review and actual PostgreSQL evidence remain required.
