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
