# KAN-207 — Live assistant scope / Ámbito vivo del asistente

## ES

Yohanna; único revisor solicitado: Anas. **Deadline Jira: 25/11/2026**, mañana respecto al 24/11. Base independiente: `dev@357cad1`, tras #97 y #122. No depende del PR #123 ni del follow-up #121.

La cobertura previa de KAN-207 verificaba asistencia y competencias. Este incremento enlaza las superficies nuevas del asistente: documentos de curso, herramientas de asistencia/competencias/entregas pendientes y contexto de una entrega.

Dos escenarios de integración:

1. El docente abre dos sesiones; crea una actividad y entrega sintéticas; añade un colega mediante la API real de equipo y después se retira de COH-IA. Los mismos tokens siguen autenticados, pero pierden documentos/datos/contexto de esa cohorte y no pueden revisar la entrega. COH-DATA sigue accesible. Se verifica con una sesión independiente que la entrega conserva estado, revisión, fecha y matrícula. Restituir el permiso por API recupera acceso sin otro login.
2. Un coder con dos sesiones puede consultar documentos y sus propias entregas mientras su matrícula está activa; al pasar a baja voluntaria pierde esos accesos, aunque las sesiones sigan autenticadas. Las herramientas académicas de cohorte son de personal autorizado: devuelven 403 tanto antes como después, incluso añadir su ID de matrícula al resumen de asistencia no concede permiso. La baja se prepara únicamente en el fixture: no afirma que exista una UI/API de baja implementada.

Los documentos se cargan del corpus sintético aceptado; se deshabilitan embeddings externos y se fija la fecha de referencia del banco. No se puentea el principal ni se simula la autorización. El caso docente usa la API de equipo y conserva otro docente para respetar la regla de no dejar la cohorte sin responsable.

Validación local: Ruff, compilación Python y diff correctos. PostgreSQL/pytest no ejecutados localmente. Por petición del usuario no se espera ni se comprueba el cierre de CI. No cambia API, permisos, modelos, Jira ni aceptación final.

## EN

Owner Yohanna; sole requested reviewer Anas. **Jira deadline: 2026-11-25**, next day from November 24. Independent `dev@357cad1` base after #97/#122; no dependency on #123 or pending #121.

Extends earlier attendance/competency revocation coverage to the document assistant and academic tool endpoints. A real teaching-team API removal must immediately affect two existing tokens across documents, attendance/competencies/pending deliveries and submission context. Other-cohort reads remain available, denied review leaves the submission unchanged, and API reinstatement restores access without a fresh login. An independent DB session observes persisted submission state.

A second scenario verifies the coder can read documents and its own enrollment submissions while active, then loses both after fixture-only voluntary withdrawal, with authentication still valid. Cohort academic tools remain staff-only and return 403 before and after; supplying an enrollment ID does not grant attendance-tool access. This does not claim an implemented withdrawal UI/API.

Tests use the repository's synthetic course corpus, fixed bank reference date and disabled external embeddings. They neither bypass principal loading nor replace authorization. Teacher team changes preserve another cohort teacher.

Local lint, Python compilation and diff checks passed. PostgreSQL tests were not run locally. CI completion is deliberately not checked. No product policy/schema/API changes, Jira updates or blanket task acceptance.

## CI correction / Corrección de CI — 24/11/2026

ES: el fallo de la ejecución 45370411124 era la expectativa 200 del coder sobre `/tools/attendance-summary` de cohorte. Se corrigió el test conforme a `cohort_access`, `_summary_access` y la cobertura de permisos ya existente; no se ampliaron permisos ni se cambió producto. Se añadió el control positivo de entregas propias y su denegación tras baja. Ruff, compilación y diff comprobados; PostgreSQL local no disponible. No se espera a la nueva CI.

EN: run 45370411124 failed because the new test wrongly expected coder access to a cohort-wide tool. The correction follows existing authorization rather than widening it, and adds a positive own-submission control plus post-withdrawal denial. Local lint/compilation/diff checked; PostgreSQL unavailable. New CI completion is not awaited.
