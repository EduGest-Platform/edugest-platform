# KAN-127 — CRM transaction rollback / Rollback transaccional CRM

## ES

Yohanna; revisión solicitada solo a Anas. Deadline **19/11/2026 (vencido)**. Incremento sobre `dev@112c33d`.

Tres casos inyectan un fallo de flush, auditoría o commit después de crear una candidatura por HTTP. Una sesión de BD nueva verifica que la etapa, la persona, los eventos y la auditoría de éxito no cambian tras el 500. Tras retirar el fallo, el mismo contacto se puede guardar una sola vez con autor y auditoría mínima, sin copiar el resumen libre a metadata.

Son pruebas de la persistencia existente, no una nueva API ni un cambio de próximos pasos. Esos campos y la aceptación completa de KAN-127 no se dan por terminados. Solo PostgreSQL sintético desechable, sin modificaciones de bases compartidas.

Local: Ruff y compilación Python correctos; pytest con PostgreSQL no ejecutado localmente. CI se lanza al abrir el PR, pero no se espera ni se declara su resultado, por indicación del usuario.

## EN

Owner Yohanna; sole requested reviewer Anas. Deadline **2026-11-19 (overdue)**. Based on `dev@112c33d`.

Three injected flush/audit/commit failures check durable rollback using independent DB sessions. A recovered request records exactly one new event and success audit without changing person/stage or copying free text into audit metadata. This validates existing persistence, not a new next-action contract or full Jira acceptance.

Local Ruff and Python compilation passed. Real-PostgreSQL pytest was not run locally. CI is not awaited or represented as passed, per user instruction. Synthetic disposable fixtures only; no shared DB changes.
