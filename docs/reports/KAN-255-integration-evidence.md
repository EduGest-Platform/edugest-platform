# KAN-255 — Evidence and limitations / Evidencias y limitaciones

**Snapshot / Instantánea:** 2026-11-23, `dev@988d9364bbbae7806ae908b32679f751e4cb287a`. Owner / responsable: Yohanna. Requested reviewer / revisor solicitado: Anas.

## Alcance / Scope

ES: inventario verificable del código integrado, sus pruebas y límites. Complementa el inventario histórico KAN-32: no sustituye sus hashes ni certifica producción. Deadline Jira **03/12/2026**, aún no vencido; la descripción conserva una propuesta 04/12. Dependencia declarada: PF2-REL-01. Se puede preparar esta instantánea ahora; la aceptación final de release sigue pendiente. No actualiza Jira.

EN: auditable inventory of integrated source, tests and limitations. It supplements the historical KAN-32 inventory without replacing its hashes or certifying production. Jira due date is **2026-12-03**, not overdue; the description retains a proposed December 4 date. Declared dependency: PF2-REL-01. This snapshot can be prepared now; final release acceptance remains pending. Jira is unchanged.

## Evidencia ejecutada / Executed evidence

- [CI at the pinned commit / CI en el commit fijado](https://github.com/EduGest-Platform/edugest-platform/actions/runs/45141296197): successful / correcto; web, API, automation, RAG, dropout, secrets and Compose jobs.
- [Registration browser run / Registro en navegador](https://github.com/EduGest-Platform/edugest-platform/actions/runs/45141295787): successful / correcto. The workflow runs the synthetic scenario twice / ejecuta el escenario sintético dos veces.

ES: `VERIFIED_RUNNING` se limita a esos comandos y entorno CI. Las rutas de la tabla son evidencia de código y casos de prueba (`CODE_PRESENT_NOT_RUN` si se considera su ejecución local aquí), no garantía de cobertura exhaustiva. No se ejecutó PostgreSQL local para este PR documental.

EN: `VERIFIED_RUNNING` is limited to those CI commands and environment. Table paths identify source and test cases (`CODE_PRESENT_NOT_RUN` for their local execution here), not exhaustive coverage. Local PostgreSQL was not run for this documentation PR.

## Matriz / Matrix

| Área / Area | Fuente / Source | Prueba / Test | Evidencia disponible / Available evidence | Límite / Limitation |
|---|---|---|---|---|
| Registro y CRM / Intake and CRM | [source](../../api/app/modules/admissions/router.py) | [test](../../api/tests/test_crm_audit.py) | Persona, candidatura, eventos e historial persistidos. / Persisted person, application, events and history. | No demuestra el flujo completo decisión humana → matrícula. / Does not establish the full human-decision-to-enrollment flow. |
| Identidad y ámbito / Identity and scope | [source](../../api/app/modules/identity/router.py) | [test](../../api/tests/test_rbac_regression.py) | Sesiones y comprobaciones backend por rol y ámbito. / Sessions and backend role/scope checks. | No certifica permisos de endpoints aún no implementados. / Does not certify unimplemented endpoints. |
| Requisitos / Requirements | [source](../../api/app/modules/requirements/router.py) | [test](../../api/tests/test_requirement_reviews.py) | Revisión versionada y panel conectado al servidor. / Versioned reviews and server-connected panel. | La evidencia orienta revisión humana; no aprueba admisión. / Evidence supports human review, not admission approval. |
| Preselección / Preselection | [source](../../api/app/modules/preselection/router.py) | [test](../../api/tests/test_preselection_closure.py) | Política, alertas de silencio y decisiones con auditoría. / Policy, silence evidence and audited decisions. | La UI nueva de alertas de #92 está pendiente; no pertenece a esta base. / New alert UI in #92 is pending and excluded from this baseline. |
| Recordatorios / Reminders | [source](../../api/app/modules/automation/reminders.py) | [test](../../api/tests/test_simulated_reminders.py) | Preparación y ejecución simuladas con controles. / Controlled simulated preparation/execution. | No prueba correo real, scheduler ni cobertura de jornada/entrevista. / Does not prove real email, scheduling or selection-day/interview coverage. |
| Asistencia / Attendance | [source](../../api/app/modules/attendance/router.py) | [test](../../api/tests/test_attendance.py) | Registro y consulta académica con control de ámbito. / Scoped academic recording and reads. | Coder no dispone de autoservicio de asistencia en esta base; faltan herramientas conectadas del asistente. / No coder attendance self-service or connected assistant tool on this baseline. |
| Competencias / Competencies | [source](../../api/app/modules/competencies/router.py) | [test](../../api/tests/test_competencies.py) | Framework publicado, asignación a cohorte e historial. / Published framework, cohort binding and history. | No equivale a endpoints de entregas/rúbricas; vistas académicas siguen locales. / Not submission/rubric endpoints; academic views remain local. |
| Seed académico / Academic seed | [source](../../api/tests/test_seed_academic.py) | [test](../../api/tests/test_seed_academic.py) | Fixtures sintéticos y comprobaciones de integridad. / Synthetic fixtures and integrity assertions. | Cien personas sintéticas no son cien muestras elegibles para ML ni datos reales. / One hundred synthetic people are not one hundred eligible ML samples or real data. |
| Conocimiento / Knowledge | [source](../../api/app/modules/knowledge/ingest.py) | [test](../../api/tests/test_knowledge_ingest.py) | Ingesta, corpus y restricciones de privacidad presentes. / Ingestion, corpus and privacy restrictions present. | Gemini #81 sigue pendiente; no se certifica asistente conversacional conectado. / Gemini #81 remains pending; no connected conversational assistant is certified. |
| GitHub | [source](../../api/app/modules/integrations/github/service.py) | [test](../../api/tests/test_github_integration.py) | Consumidor de solo lectura con validación y pruebas. / Validated read-only consumer and tests. | No hay router GitHub montado ni persistencia de PortfolioLink en este incremento. / No mounted GitHub router or persisted PortfolioLink in this increment. |
| ML abandono / Dropout ML | [source](../../ml/dropout/train.py) | [test](../../ml/dropout/tests/test_score_card.py) | Entrenamiento, evaluación y scoring offline sintéticos. / Synthetic offline training, evaluation and scoring. | Sin adaptación a datos vivos, alerta de producto ni validación predictiva real. / No live-data adapter, product alert or real predictive validation. |
| Métrica administrativa / Administrative metric | [source](../../evals/automation/run_metrics.py) | [test](../../evals/automation/test_metric_runner.py) | Runner y escenarios hipotéticos reproducibles. / Reproducible runner and hypothetical scenarios. | No demuestra ahorro medido del 70%; faltan catálogo/unidades y aceptación. / Does not establish measured 70% savings; catalogue/units and acceptance remain pending. |
| Arranque y navegador / Startup and browser | [source](../../infra/compose.yaml) | [test](../../e2e/f1-registration.mjs) | CI Compose y registro de navegador ejecutados sobre datos sintéticos. / Compose and browser registration CI executed with synthetic data. | CI efímero no acredita despliegue público, disponibilidad ni aceptación final. / Ephemeral CI does not establish public deployment, availability or final acceptance. |

## Pendiente e independiente / Pending and independent

ES: [#92](https://github.com/EduGest-Platform/edugest-platform/pull/92) conecta las alertas a la UI, pero no es dependencia de este documento. [#81](https://github.com/EduGest-Platform/edugest-platform/pull/81) implementa embeddings; su contenido tampoco se considera integrado. Revalidar estados al revisar: esta tabla no sigue automáticamente futuras fusiones.

EN: #92 connects the alert UI but is not a dependency of this document. #81 implements embeddings and is also excluded from integrated evidence. Recheck states during review: this snapshot does not automatically track future merges.

## Riesgos y siguiente comprobación / Risks and next verification

1. ES: conservar la separación de fuentes API/demo: los módulos locales son `MOCK` respecto a persistencia y autorización. EN: preserve API/demo separation; local modules are `MOCK` for persistence and authorization.
2. ES: antes del gate de release, repetir CI sobre el SHA candidato, enlazar resultados y revisar recorridos todavía ausentes (decisión/matrícula, entregas, asistente). EN: before release, rerun CI on the candidate SHA, link results and review missing decision/enrollment, submission and assistant flows.
3. ES: la revisión técnica de Anas no sustituye aceptación de PO/cliente, matriz ética ni decisiones sobre unidades/tiempos del 70%. EN: technical review by Anas does not replace PO/client acceptance, ethical review or the 70% units/time decisions.
4. ES: no desplegar ni ejecutar migraciones sobre bases compartidas para validar este documento. EN: validate documentation without deployments or shared-database migrations.

## Reproducir y mantener / Reproduce and maintain

```sh
git show 988d9364bbbae7806ae908b32679f751e4cb287a:.github/workflows/ci.yml
gh run view 45141296197 --json headSha,status,conclusion,jobs
gh run view 45141295787 --json headSha,status,conclusion,jobs
```

ES: se comprobaron todas las rutas relativas de esta matriz contra el árbol de trabajo y `git diff --check`. Cada actualización debe fijar otro SHA y sus ejecuciones; no trasladar el verde de esta base a código nuevo.

EN: all relative matrix paths were checked against the working tree, together with `git diff --check`. Each update must pin a new SHA and its runs; do not transfer this baseline green status to new code.
