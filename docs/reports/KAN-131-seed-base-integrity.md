# KAN-131 — Base seed integrity / Integridad del seed base

## ES

Responsable: Yohanna. Revisor GitHub solicitado: **Anas**. Deadline Jira: **23/11/2026 (hoy)**; la propuesta 19/11 de la descripción es distinta. Base: `dev@6b58e0f`.

El seed existente importa el dataset compartido y su CLI reconcilia datos académicos. Este incremento añade siete pruebas de regresión sobre PostgreSQL real, sin otro cargador ni cambios de producto:

1. Programas, convocatorias, fechas, aforo y vínculos cohorte/convocatoria coinciden con la configuración fuente.
2. Cada persona conserva referencia, identidad sintética y correo normalizado, sin duplicados.
3. Las candidaturas conservan estado y convocatoria, generan evento de importación y secuencias únicas; los borradores del navegador no se importan como expedientes.
4. Staff conserva exactamente los roles y ámbitos definidos, sin privilegios adicionales.
5. Aspirante/coder reutilizan su Person sin recibir roles internos; las matrículas del dataset conservan cohorte y estado.
6. Repetir el comando normal conserva una candidatura posterior, su contacto CRM, cambios de aforo, una revocación de rol y las identidades de las tablas. El test prohíbe llamar a reset durante esa repetición.
7. En la BD de pruebas vacía, el comando crea datos base y académicos; una segunda ejecución reutiliza sus IDs.

Se comprueba `main()` (el comando público), no `seed(db)` dos veces: la función interna inserta la base y el CLI decide cuándo usarla. El único reset explícito del nuevo archivo se limita al fixture PostgreSQL desechable que ya usa toda la suite; nunca se dirige a staging ni a bases compartidas.

Los estados históricos importados no crean retrospectivamente decisiones humanas ni evidencias de matrícula desde admisión. Son fixtures sintéticos; no demostrarían por sí solos el recorrido completo ni validez ML. Los tests académicos de KAN-173 siguen comprobando sus cálculos; este PR cubre integridad de la base y preservación al repetir el comando, sin duplicar el cargador.

Local: Ruff, compilación Python y `git diff --check` correctos. Pytest completo y PostgreSQL no se ejecutaron localmente; CI ejecuta el archivo y adjunta los totales con KAN-219. La presencia de pruebas no cierra Jira ni sustituye revisión humana.

## EN

Owner: Yohanna. Sole requested GitHub reviewer: **Anas**. Jira deadline: **2026-11-23 (today)**; the description's November 19 proposal is separate. Based on `dev@6b58e0f`.

Seven real-PostgreSQL regressions cover the existing shared seed: catalogue/call/cohort bindings; synthetic person identity; persisted application states, import events and sequences without browser drafts; exact staff grants; person accounts without staff roles and linked enrollments; non-destructive normal CLI reruns after later intake/CRM/capacity/revocation changes; and empty-test-database bootstrap followed by ID-preserving rerun.

The tests drive `main()`, whose guard skips an existing base, rather than calling insert-only `seed(db)` twice. Only the existing disposable PostgreSQL fixture is explicitly reset in the bootstrap case. No shared/staging DB is used and no product loader changes are introduced.

Imported historical stages do not fabricate human decisions or admission-to-enrollment evidence. Synthetic fixtures do not establish a full production journey or ML validity. KAN-173's academic calculation coverage remains separate.

Local Ruff, Python compilation and diff checks passed. Full pytest/PostgreSQL were not run locally; existing CI includes the new tests and KAN-219's count-only artifact. No Jira completion or automatic acceptance is implied.
