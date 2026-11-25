# Stored states and workflow boundaries / Estados y límites de flujo

## EN — Canonical

The [generated schema reference](schema-reference.md) describes registered SQLAlchemy models, not a running database. Its text-domain index includes only complete simple text `IN` checks. Compound constraints are preserved in the full dictionary. Numeric checks, conditional invariants and arbitrary SQL expressions are not interpreted as workflow state machines.

A legal stored value does not authorize a transition. API/session checks and service transactions decide whether a person may act. This reference is implementation documentation, not PO acceptance or evidence of PostgreSQL execution.

| Domain | Stored boundary | Transition/authorization source | Relevant tests |
|---|---|---|---|
| Call | `estado` is the admission window; `publication_state` is editorial visibility | [publication service](../../api/app/modules/catalog/publication_service.py), [registration](../../api/app/modules/admissions/service.py) | [publication security](../../api/tests/test_catalog_publication_security.py), [draft registration](../../api/tests/test_draft_registration.py) |
| Admission | Application stages and final `SelectionDecision` outcomes are distinct from individual votes | [selection service](../../api/app/modules/selection/service.py); human quorum, capacity and provenance | [quorum](../../api/tests/test_selection_quorum.py), [decisions](../../api/tests/test_selection_decisions.py) |
| Enrollment | Academic `estado` and documentary `documentation_state` are independent | [documentation service](../../api/app/modules/learning/documentation_service.py); global administration, coherent admission and version checks | [documentation security](../../api/tests/test_enrollment_documentation_security.py) |
| Staff access | Invitation use, active profile and approved/applied access request are separate facts | [staff service](../../api/app/modules/staff/service.py); invitation acceptance grants no role; approval does not apply one | [staff security](../../api/tests/test_staff_security.py), [access review](../../api/tests/test_staff_access_review.py) |
| Competencies | Framework draft/publication/archive are versioned storage states | [competency service](../../api/app/modules/competencies/service.py); assigned cohort/role and immutable published versions | [competency tests](../../api/tests/test_competencies.py) |
| Discussions | Resolution and comment deletion are separate lifecycle facts | [discussion service](../../api/app/modules/discussions/service.py); scoped authorization and optimistic versions | [discussion tests](../../api/tests/test_discussion_lifecycle.py) |
| Risk evidence | Model status and human review state are not learner outcomes | [risk models](../../api/app/modules/risk/models.py); synthetic advisory evidence, no automatic adverse action | [risk model tests](../../api/tests/test_risk_evidence_models.py) |

The links identify code/test sources; they do not claim every suite was run during this documentation change. Database triggers defined only in migrations and API-only constraints are not inferred from model metadata. Keep `alembic check`, authorization tests and human review separate from generated-document freshness.

## ES

La [referencia generada](schema-reference.md) describe modelos registrados, no una base ejecutándose. El índice de dominios solo interpreta CHECK completos `columna IN ('texto', ...)`; conserva íntegros los compuestos en el diccionario. No interpreta restricciones numéricas, invariantes condicionales o expresiones SQL arbitrarias como máquinas de estados.

Un valor válido en persistencia no autoriza una transición. La sesión, los permisos y las transacciones del servicio determinan quién puede actuar. La tabla anterior enlaza las fuentes de admisión/publicación, decisión humana, matrícula/acreditación, invitación/acceso, competencias, comentarios y evidencia de riesgo. No acredita aceptación PO ni ejecución de esas suites.

La publicación no abre una convocatoria cerrada; acreditar documentos no cambia el estado académico; aceptar invitación o aprobar acceso no aplica roles. Los estados de riesgo no deciden resultados de personas. Las restricciones del API y los triggers exclusivos de migraciones no se deducen de los modelos. Frescura documental, `alembic check`, pruebas de autorización y revisión humana son controles distintos.
