# KAN-225 — Explicit application / Aplicación explícita

## ES

Incremento del 25/11/2026, posterior al stack de invitaciones. Orden: contratos → previsualización → aplicación transaccional → consulta → seguridad. La aprobación sigue sin conceder roles; no se declara terminada KAN-225.

- `GET /api/v1/staff/access-requests/{id}/application-preview`: administración global, bloqueos actuales sin modificar roles. No reserva ni garantiza una aplicación posterior.
- `POST .../{id}/apply`: administración global distinta del solicitante, `confirm: true` booleano estricto y repetición exacta de `requested_role`, `scope_type`, `scope_id`. Revalida cuenta interna activa, ficha activa, revisión y ámbito; crea y vincula una asignación nueva en la misma transacción que la auditoría.
- `GET .../{id}/application`: propietario con ficha activa o administración global. Solicitud ajena: 404. No revela asignaciones cuyo usuario, rol, ámbito o identificador no coincidan.
- Un acceso activo previo bloquea la aplicación, nunca se toma prestado. Reintentar devuelve la asignación original sin reactivar accesos revocados. `assignment_active` solo indica que esa fila no está revocada, no garantiza acceso efectivo ni cuenta activa.
- No cambia KAN-222, permisos, modelos, migraciones, cuentas, correo ni interfaz. La revocación por solicitud queda pendiente; se conserva la revocación existente del equipo docente. Auditoría con identificadores y ámbito, sin nombres ni secretos.

Bloqueos: ámbito primero (cohorte compartida con gestión docente), usuario `FOR NO KEY UPDATE`, ficha y solicitud. Se recargan los valores bloqueados y se rechaza un cambio de destinatario o ámbito. El bloqueo del usuario permite comprobaciones FK `KEY SHARE`; no se promete unicidad frente a escritores externos que omitan este protocolo.

## EN

Explicit application follows the invitation stack. Approval alone never grants roles. Global administrators preview and apply; applicants cannot apply their own requests. Confirmation echoes the exact stored role/scope using literal JSON true. Eligibility is rechecked under locks; assignment, request transition and audit commit together.

Status is restricted to the active owner or global administration. Foreign requests return 404. Assignment links are verified against owner, role, scope and ID. Existing active grants cause a conflict rather than being adopted. Repeated application returns the original assignment and never reactivates a revoked grant. `assignment_active` describes the row, not effective authorization.

Lock order: scope, user (`FOR NO KEY UPDATE`), profile, request. The user lock permits foreign-key `KEY SHARE` checks: [PostgreSQL row lock compatibility](https://www.postgresql.org/docs/16/explicit-locking.html#LOCKING-ROWS). This is not a database uniqueness constraint against unrelated writers.

Request-based revocation, provisioning, mail, UI and KAN-222 remain outside this increment. No schema, permission or shared account changes. Audit contains identifiers and scope, no names or tokens. KAN-225 remains partial.

## Validation / Validación

Offline regressions exercise strict confirmation, blockers, link verification, lock SQL and authorization before resource lookup. PostgreSQL cases cover scope, idempotency, owner isolation, revoked grants, conflicting requests and rollback after audit failure. PostgreSQL cases are supplied and collected only: no local runtime was available. Real concurrent transactions are not claimed as validated. Run the repository PostgreSQL suite before merging. CI completion is not awaited.
