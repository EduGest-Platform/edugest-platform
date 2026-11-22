# KAN-144 — Handoff history and live authorization / Historial y autorización vigente

## ES

Incremento parcial sobre dev `26e5199`. Prueba de integración API/PostgreSQL del paso humano a selección (`convocada`) ya implementado en #46. No es un handoff tras admisión ni añade asignación de tareas, matrícula, rol nuevo o política de retirada de permisos.

Cinco casos ejecutables: tras crear contacto con resultado y revisión no satisfecha por captación, selección convoca y otra sesión verifica identidad, campos, fecha original, orden de eventos, autor/fecha del contacto, revisión y decisión persistida. Una segunda prueba modifica la revisión con selección y comprueba que la primera revisión conserva su autor, motivo y fecha. Dos casos revocan los permisos del personal sintético mediante fixture: el token sigue autenticado pero las lecturas históricas y nuevas notas se deniegan sin borrar el historial, que administración conserva. Otro caso comprueba que pasar a selección no amplía el ámbito de personal de otro programa.

Las revocaciones solo se hacen en la BD sintética desechable de las pruebas. No implementan una operación de administración ni significan que convocar deba revocar captación automáticamente: ese cambio de política no se inventa aquí. Se comprueba la autorización vigente por solicitud, en vez de convertir la autoría histórica en permiso permanente.

Sin código de producción, migración, contrato, seed o Jira modificados. No se duplica el caso simple de cambio de etapa: se conectan CRM, versiones, decisión humana, nueva sesión y permisos revocados. La parte completa de KAN-144 tras admisión/asignación sigue pendiente de sus contratos.

## EN

Partial KAN-144 integration regression for the implemented human call-to-selection transition, not a post-admission handoff or a new task/permission policy. Five cases join real API writes and PostgreSQL persistence: prior contact/review preserved across a new session, later selection amendment preserving the original review revision, two existing-token revocation cases without historical data loss, and foreign-program access denied before/after calling.

Synthetic DB fixtures revoke assignments directly only to test live authorization. This does not add a staff-management API or automatically revoke recruitment permissions at handoff. Historical authorship must not become permanent access. No production code/schema/contract/seed/Jira changes. Full admission/enrollment/task reassignment remains out of scope.

## Evidence / Evidencia

Local ruff and compilation PASS; PostgreSQL/Docker unavailable locally, NOT RUN. Current-head CI must run `api/tests/test_handoff_history.py` with the full API suite. Results recorded in the PR, never inferred from source. Review: David primary (Jira reviewer), Elizabeth secondary (scope and backend). No task-completion claim.
