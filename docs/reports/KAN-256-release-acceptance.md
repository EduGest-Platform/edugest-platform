# KAN-256 · Evidencia de aceptación del MVP / MVP acceptance evidence

**Base revisada / Reviewed baseline:** `dev@67357d0`, 28/11/2026.
**Responsable / Owner:** Elizabeth. **Revisión / Reviewer:** Yohanna.

**ES** — Matriz técnica para la revisión de evidencias del recorrido prioritario y los objetivos del proyecto. Los resultados remotos corresponden al SHA indicado. La aceptación funcional y las comprobaciones del entorno se registran en sus tickets.

**EN** — Technical evidence matrix for the priority journey and project objectives. The remote results refer to the listed SHA. Product acceptance and environment checks are recorded on their respective issues.

| Criterio de entrega / Delivery criterion | Evidencia inspeccionada / Evidence inspected | Pendiente de aceptación / Acceptance remaining |
| --- | --- | --- |
| Candidatura, requisitos, preselección y decisión humana / Application, requirements, preselection and human decision | Revisión con ámbito, quórum y votos, inscripción pública y recorrido F2. / Scoped review, quorum and voting, public intake and F2 journey. [Preselección / Preselection](KAN-256-preselection-acceptance.md) · [Reglas de decisión / Decision rules](KAN-147-decision-rules.md) | Reconciliar la formalización independiente y las reglas de cupo y espera con las decisiones de producto. / Reconcile separate formalization and the capacity and waitlist rules with product decisions. |
| Matrícula, asistencia y competencias / Enrollment, attendance and competencies | F2 repite matrícula y asistencia sobre PostgreSQL. Los recorridos de analítica y progreso comprueban datos sintéticos y ámbito. / F2 replays enrollment and attendance on PostgreSQL. Overview and progress journeys exercise synthetic records and scope. [F2](../../e2e/F2-admission-enrollment.md) · [Activación por cohorte / Cohort activation](KAN-54-training-activation-policy.md) | Ensayo con el perfil autorizado y revisión funcional de los estados. / Rehearse with the authorized profile and review lifecycle states. |
| Automatización del 70 % / 70% automation target | Evaluador, inventario de tareas y escenarios hipotéticos reproducibles. / Evaluator, task inventory and reproducible hypothetical scenarios. [Métricas / Metrics](KAN-199-metric-runner.md) | Validar catálogo, unidad y ejecuciones elegibles con evidencia aprobada. Ahorro real sin medir. / Validate the catalogue, unit and eligible executions with approved evidence. Actual savings remain unmeasured. |
| Asistente con citas y ámbito / Scoped assistant with citations | Banco de preguntas y controles de ámbito disponibles. El recorrido de teclado verifica respuesta, fallo, cancelación y foco. / A question bank and scope controls are available. The keyboard journey covers response, failure, cancellation and focus. [Ámbito / Scope](KAN-207-live-assistant-scope.md) · [Prueba Chromium / Chromium test](../../e2e/assistant-keyboard.mjs) | Confirmar en el entorno autorizado el corpus y el comportamiento de cita o abstención. / Confirm the corpus and citation or abstention behavior in the authorized environment. |
| Riesgo de abandono y revisión humana / Dropout risk and human review | Baseline sintético, evaluación y seguimiento local. / Synthetic baseline, evaluation and local tracking. [Experimento / Experiment](../../ml/README.md) | Las vistas de alertas siguen en revisión. Validar límites y revisión humana antes de aceptación. / Alert views remain under review. Validate limits and human review before acceptance. [#273](https://github.com/EduGest-Platform/edugest-platform/pull/273) |
| Feedback revisado por docentes / Teacher-reviewed feedback | El backend guarda borradores versionados y publica por aprobación explícita. / The backend versions drafts and requires explicit approval to publish. [#272](https://github.com/EduGest-Platform/edugest-platform/pull/272) | Integrar y verificar la pantalla de revisión. / Integrate and verify the review screen. [#274](https://github.com/EduGest-Platform/edugest-platform/pull/274) |
| Demo segura, respaldo y documentación / Secure demo, fallback and documentation | CI y F1 E2E en verde para la base revisada. Hay guía de respaldo y comprobación de restauración desechable. / CI and F1 E2E passed on the reviewed baseline. The local fallback guide and disposable restore evidence are available. [CI](https://github.com/EduGest-Platform/edugest-platform/actions/runs/46095100362) · [F1](https://github.com/EduGest-Platform/edugest-platform/actions/runs/46095100396) · [Respaldo / Fallback](../deploy/KAN-212-local-fallback.md) | Registrar el ensayo humano y el gate del entorno, completar la revisión de los manuales y recoger aceptación. / Record the presenter rehearsal and environment gate, finish manual reviews and capture acceptance. |

## Registro para la versión candidata / Release candidate record

**ES** — Al preparar la versión para el ensayo, pegar el SHA candidato y los enlaces a CI y F1 para ese mismo SHA. Para cada fila, enlazar la evidencia ejecutada y registrar fecha, entorno, resultado y quién acepta. Si una prueba vive en un PR abierto, registrar el PR como pendiente de integración. Si falta evidencia del candidato, usar `NOT_RUN` y señalar quién debe obtenerla.

**EN** — For the rehearsal candidate, record the candidate SHA and link CI and F1 runs for that SHA. For each criterion, link the executed evidence and record date, environment, outcome and approver. Track tests from open PRs as pending integration. When candidate evidence is missing, record `NOT_RUN` and identify who will obtain it.

| Evidencia por reconciliar / Evidence to reconcile | Registro del candidato / Candidate record |
| --- | --- |
| Segunda entrevista individual / Second individual interview | [#309](https://github.com/EduGest-Platform/edugest-platform/pull/309) · Pendiente / Pending |
| Alertas y publicación de feedback / Alerts and feedback publication | [#273](https://github.com/EduGest-Platform/edugest-platform/pull/273) · [#274](https://github.com/EduGest-Platform/edugest-platform/pull/274) · Pendiente / Pending |
| Gate de seguridad y ensayo / Security gate and rehearsal | [#308](https://github.com/EduGest-Platform/edugest-platform/pull/308) · [#310](https://github.com/EduGest-Platform/edugest-platform/pull/310) · Pendiente / Pending |
| Carga sintética y sus límites / Synthetic seed and its limits | [#312](https://github.com/EduGest-Platform/edugest-platform/pull/312) · Pendiente / Pending |

### Verificar CI y F1 en el SHA candidato / Verify CI and F1 on the candidate SHA

**ES** — Desde el repositorio, consultar las ejecuciones del SHA completo que se quiere aceptar. Usar ejecuciones de integración (`push` a `dev`) para evaluar ese candidato. Registrar el enlace de CI y el de F1 solo cuando ambos tengan el mismo `headSha` y hayan terminado en `success`. Un resultado de una rama hija sirve como evidencia de esa rama.

**EN** — From the repository, inspect runs for the full SHA under review. Use integration runs (`push` to `dev`) for that candidate. Record CI and F1 links when both show the same `headSha` and completed with `success`. A child branch run is evidence for that branch.

```sh
candidate='<full candidate SHA>'
gh run list --branch dev --event push --commit "$candidate" --limit 20 \
  --json name,headSha,status,conclusion,url
```

| Resultado / Result | Qué anotar en el acta / What to record |
| --- | --- |
| CI y F1 completados con éxito para el candidato / CI and F1 completed successfully for the candidate | Enlaces, SHA y entorno que ejecutó las comprobaciones. La aceptación humana se registra aparte. / Links, SHA and execution environment. Record human acceptance separately. |
| Ejecución pendiente o ausente / Pending or missing run | Identificar el workflow y conservar el resultado como pendiente o `NOT_RUN`. / Identify the workflow and keep the outcome pending or `NOT_RUN`. |
| Ejecución fallida o cancelada / Failed or cancelled run | Enlazar la ejecución y registrar el check bloqueante para ese SHA. / Link the run and record the blocking check for that SHA. |

**Estado / Status:** revisión técnica completada para esta base. La conformidad con el briefing y la aceptación de producto quedan para revisión de Elizabeth y Yohanna. / Technical reconciliation complete for this baseline. Elizabeth and Yohanna still need to review briefing conformance and product acceptance.

[Alcance y fechas / Scope and dates](KAN-211-scope-freeze-proposal.md) · [Plan de proyecto / Project plan](../../projectplan.md)
