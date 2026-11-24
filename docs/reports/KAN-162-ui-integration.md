# KAN-162 — UI integration / Integración UI

## ES

Implementación: Yohanna. Tarea asignada a Anas; único revisor solicitado: Anasfady. Deadline Jira: **19/11/2026**. Incremento del 24/11/2026.

Conecta deliberación al expediente servidor: cupos comparativos, votos pendientes, evidencia histórica y confirmación humana antes de votar. La API conserva autoridad sobre ámbito, firmas, etapas y cupo. Protege el motivo sin guardar al cerrar el expediente.

## EN

Implementation: Yohanna. Jira assignee: Anas. Sole requested reviewer: Anasfady.

Connects the server application file to comparative selection capacity, pending votes and historical evidence. Voting requires explicit human confirmation; 202 never claims admission. Backend authorization, quorum and capacity remain authoritative.

## Validation / Validación

PASS: TypeScript, 82 Vitest tests (including empty evidence, disagreement preservation and HTML escaping), production build and diff checks.

## Limits / Límites

Browser/live multi-person workflow not run locally. / Recorrido navegador con varias personas no ejecutado localmente. Admission requires an existing cohort ID; interview scoring and scheduling remain separate.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.

## Review correction / Corrección de revisión — 24/11/2026

ES: El botón Cerrar del pie del expediente usa ahora el mismo cierre protegido del modal que Escape, el fondo y la X. `Modal.footer` admite una función que recibe ese cierre, manteniendo los pies existentes compatibles. Cancelar no ejecuta `onClose`, por lo que conserva el formulario y su motivo; aceptar descarta explícitamente. Dos regresiones ejercitan el cierre real recibido por el pie con confirmación cancelada/aceptada y formulario limpio. TypeScript, 84 pruebas Vitest y compilación correctos; prueba de navegador no ejecutada.

EN: The application footer now receives Modal's guarded close callback, shared with Escape, backdrop and X. Existing static footers remain compatible. Cancelling does not invoke `onClose`, leaving the form and unsent reason mounted; accepting explicitly closes it. Two component regressions exercise the real footer callback for cancel/accept and clean closure. TypeScript, 84 Vitest tests and production build passed; browser interaction was not run locally.
