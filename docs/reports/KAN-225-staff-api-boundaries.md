# KAN-225 — Staff API review / Revisión de API interna

## ES

Este stack implementa una parte de KAN-225 sobre los modelos integrados de KAN-223. No declara terminada la tarea ni aprobada la decisión de producto KAN-222.

Orden: contratos → emisión y rotación → aceptación → solicitudes y revisión → regresiones de seguridad. Cada PR tiene como base la rama del anterior; revisar el diff contra esa base y fusionar desde el primero.

- Solo la administración global existente puede emitir, renovar y revocar invitaciones o revisar solicitudes. Captación no recibe un permiso nuevo.
- La cuenta destinataria debe existir, estar activa y no tener persona asociada. No hay alta pública, creación de cuentas, correo ni pantalla nueva.
- La respuesta de emisión entrega el token una sola vez con `Cache-Control: no-store`. Almacenamiento: hash SHA-256. Tratar la respuesta como secreto; entregarla por un canal privado y no copiarla a Jira, GitHub, logs o URLs.
- Renovar invalida las invitaciones pendientes anteriores. Una invitación revocada, expirada, usada o ajena no activa la ficha. El vencimiento es exclusivo. Una ficha inactiva no se reactiva mediante invitación.
- Aceptar activa solo la ficha propia y consume el token. No modifica las asignaciones de roles.
- Una ficha activa puede solicitar acceso y consultar sus propias solicitudes. Administración global puede consultar todas, con paginación limitada a 100 registros.
- La persona administradora que revisa debe ser distinta de quien solicita. Se valida la existencia del ámbito al aprobar; la decisión queda `approved` o `rejected`, sin aplicar roles. Una segunda revisión se rechaza.

Quedan pendientes la decisión de KAN-222, aplicación de permisos, provisión de cuentas, entrega de correo e interfaz. La aplicación de roles requiere otro contrato y pruebas de privilegios; `approved` no equivale a `applied`.

Las transiciones bloquean ficha antes de invitación o solicitud. Los eventos de auditoría se escriben dentro de la misma transacción y excluyen tokens. Las pruebas PostgreSQL incluyen fallo de auditoría tras `flush`, aislamiento de listados, invalidación y revisión única. No se han ejecutado contra PostgreSQL local; la concurrencia real tampoco se declara validada. Ejecutar la suite PostgreSQL del repositorio antes de fusionar.

## EN

This stack implements part of KAN-225 using the integrated KAN-223 models. It does not close KAN-225 or approve the KAN-222 product decision.

Review and merge in dependency order: contracts, issuance/rotation, acceptance, request/review, security regressions. Global administrators manage invitations and review requests; no new recruiting permission is granted. Targets are existing active internal accounts without an associated person.

Issuance returns a one-time secret in a no-store response. Store only its SHA-256 hash and deliver privately, never in tickets, logs or URLs. Rotation invalidates pending tokens. Acceptance consumes a valid owner-bound token and activates only the profile. It never grants roles or reactivates inactive profiles.

Active staff see their own requests; global administrators see the bounded paginated list. Review requires a different actor and validates scope existence on approval. Approved/rejected decisions never create role assignments and cannot be reviewed again.

Account provisioning, email delivery, UI, role application and KAN-222 remain outside this increment. Profile locks precede invitation/request locks; audit records share the transaction and exclude secrets. PostgreSQL regressions are supplied, including rollback after an audit failure, but were not executed locally. Real concurrency is not claimed as verified. Run the repository PostgreSQL suite before merging.
