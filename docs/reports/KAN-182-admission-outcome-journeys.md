# KAN-182 — Admission outcome journeys / Recorridos de resultado

## ES

Preparado el 23/11/2026 sobre `dev@1ca7cf0`. **Deadline Jira: 20/11/2026 (vencido)**; no confundir con la propuesta 27/11 en la descripción.

Las pruebas de integración API empiezan con una inscripción pública nueva y un contacto CRM. Todas las transiciones se solicitan por HTTP mediante personas autenticadas: convocatoria a selección, admisión y matrícula, lista de espera, retirada expresa y posterior promoción desde reserva. Se comprueba persistencia en PostgreSQL, identidad de persona/cohorte, historial conservado, auditoría y rechazo de repeticiones sin escrituras adicionales.

También se intenta avanzar la candidatura desde otro programa, admitir antes de preselección, y matricular como captación, coder o anónimo. Cada intento denegado debe conservar etapa, matrículas, decisiones, eventos CRM y auditoría de decisiones. La preparación de datos solo añade una cohorte sintética y capacidad de prueba: nunca escribe etapas, decisiones ni matrículas directamente.

El incremento usa los endpoints ya integrados en #95; no implementa UI ni modifica la política de quórum pendiente en #98. Ese PR deberá revalidar/adaptar los recorridos al fusionarse. No se presenta como E2E de navegador ni cierra KAN-182/KAN-192. El orden de espera sigue siendo provisional según el contrato actual.

Comprobaciones locales: Ruff y compilación Python correctos; no se ejecutó pytest local porque no hay PostgreSQL de pruebas disponible. CI ejecuta el nuevo archivo dentro de `pytest` con PostgreSQL real y seed sintético. Revisar su resultado antes de aceptar. Único revisor solicitado: Anas.

## EN

Prepared 2026-11-23 from `dev@1ca7cf0`. **Jira deadline: 2026-11-20 (overdue)**; the description's proposed November 27 date is separate.

These API integration tests start with public intake and a CRM contact, then drive every transition over authenticated HTTP: invitation, admission with enrollment, waiting list, express withdrawal and later human promotion. PostgreSQL assertions verify person/cohort identity, durable outcomes, retained history, audit and duplicate rejection without additional writes.

Negative journeys exercise another programme, premature admission, recruitment, coder and anonymous actors. Rejected requests preserve stage, enrollments, decisions, CRM events and decision audit. Only synthetic reference cohort/capacity is prepared directly; application stages, decisions and enrollments are never assigned directly.

The tests consume #95's integrated contract; they add neither selection UI nor #98's pending quorum policy. Revalidate/adapt journeys when that policy merges. This is API integration evidence, not a browser E2E or Jira completion. Waiting order remains provisional under the current contract.

Local Ruff and Python compilation passed. Local pytest was not run because a disposable PostgreSQL test service is unavailable. CI includes the file in its real-PostgreSQL pytest suite; inspect the result before acceptance. Sole requested reviewer: Anas.
