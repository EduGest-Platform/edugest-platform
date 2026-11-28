# KAN-54 — Training activation decision / Decisión de activación formativa

27/11/2026 · Owner Elizabeth · Reviewer Anas · PO_ACCEPTED (functional scope); CODE_PRESENT_NOT_RUN for the new teacher regression locally; acceptance evidence and independent review pending. This final PO clarification supersedes the earlier teacher-or-coordinator proposal on the same date. Prior accepted KAN-123 / #247: publication and cohort assignment are distinct; a teacher authorized in a cohort may publish for its program. This decision preserves that publication authority and existing RBAC.

## ES — Decisión funcional aprobada por PO (27/11/2026)

Para el MVP, la habilitación formativa se realiza por cohorte: publicar un marco de competencias versionado del programa, asignarlo explícitamente a la cohorte y publicar actividades mediante su flujo propio.

- Responsable funcional de la asignación: **docente autorizado en la cohorte**. Coordinación no realiza esta acción; conserva sus permisos actuales de indicadores agregados en el dominio de competencias.
- La publicación y edición de marcos conservan la autoridad existente de KAN-123. No se amplían permisos ni se alteran las atribuciones administrativas existentes.
- Publicar una nueva versión no reasigna automáticamente las cohortes. Una versión archivada sigue disponible para las cohortes vinculadas; no se asigna de nuevo. Se conserva el histórico de evaluaciones.
- Registrar actor, fecha, versión anterior/nueva y auditoría. Denegar por defecto acciones fuera de ámbito.
- Las actividades mantienen su flujo independiente; no se introduce un bloqueo general por ausencia de marco.
- Sin interruptor global ni nueva entidad de plan formativo en el MVP. Cualquier ampliación requiere decisión de alcance. No cambiar catálogo público ni matrícula.

### Criterios de historia y evidencia

| Criterio | Evidencia integrada | Brecha |
|---|---|---|
| Docente habilita formación en su cohorte | #67, #130/#205–209, #269, #247; regresión de asignación en este PR | CI y demo de aceptación |
| Coordinación no asigna marcos | RBAC actual: el endpoint exige `competencies.configure`; coordinación tiene `competencies.aggregate` | Confirmar regresión 403 en CI; no ampliar permisos |
| Aislamiento por rol y ámbito | test_competencies.py: test_teacher_of_another_cohort_gets_403; #141; prueba de denegación en este PR | Confirmar CI y revisión cruzada |
| Autor, fecha y estado | CompetencyFramework.created_by/created_at/published_at/estado, CohortCompetencyFramework.assigned_by/assigned_at; eventos de creación, edición, publicación y asignación | No confundir estado del marco con estado del plan formativo |
| Modelo docente/programa/cohorte | catalog/models.py, identity/models.py, learning/team_router.py, docs/data/schema-reference.md | No añadir entidad Asignatura ni plan global para MVP |

### Casos de aceptación

1. Docente con ámbito asigna versión publicada del mismo programa; actor/fecha/versión verificables en DB y auditoría.
2. Docente sin ámbito, coordinación, captación/coder o anónimo no pueden activar; 403/401; sin mutación ni evento de éxito.
3. Publicar nueva versión no sustituye automáticamente la asignada; reasignación explícita conserva histórico.
4. Marco borrador/archivado o de otro programa no puede asignarse (409).
5. Coordinación mantiene sus permisos agregados, sin acceso adicional a evaluaciones individuales ni edición/publicación/asignación de marcos. No cambiar permisos administrativos existentes.
6. Demostrar recorrido por cohorte con datos sintéticos, actividades independientes y revisión cruzada.

### Estado de implementación

El comportamiento de asignación y la regresión 403 para coordinación coinciden con la decisión final. No se requiere un permiso nuevo para coordinación ni una interfaz adicional para este alcance. Pendientes: CI/E2E del HEAD, comprobación funcional en demo sintética y revisión independiente de Anas. No se afirma que el DoD esté completo ni se cierra la historia.

Evidencia histórica: [#247](https://github.com/EduGest-Platform/edugest-platform/pull/247), [#269](https://github.com/EduGest-Platform/edugest-platform/pull/269), [CI #271](https://github.com/EduGest-Platform/edugest-platform/actions/runs/46032355814) y [E2E #271](https://github.com/EduGest-Platform/edugest-platform/actions/runs/46032355812). No nueva ejecución local. Los cuatro hijos Jira están finalizados según la reconciliación previa; ello no acredita el DoD de la historia.

## EN — Final PO-approved functional decision (2026-11-27)

MVP training enablement is cohort-specific: publish a versioned program competency framework, explicitly assign it to a cohort, and publish activities through their independent existing workflow. The **authorized teacher** is the functional owner of assignment. Coordination does not perform assignment and retains existing competency aggregate permissions. This supersedes the earlier teacher-or-coordinator proposal. Preserve KAN-123's existing framework-edit/publication authority and existing administrative permissions; do not expand RBAC.

Publication never automatically changes existing cohort assignments. Preserve archived versions for existing links, assessment history, actor/time and previous/new version audit. Reject out-of-scope actions, coordinator/recruitment/learner assignment, anonymous requests and draft, archived or foreign-program assignments. No global plan switch, new plan entity or blanket activity block in the MVP. Preserve public admission catalogue and enrollment behavior.

**Implementation status:** the existing teacher assignment behavior and coordinator 403 regression align with the final decision. No new coordinator permission or UI is required for this scope. CI/E2E at the current HEAD, synthetic demo and independent review remain pending. Historical CI is not fresh runtime evidence. KAN-54 remains open pending acceptance evidence; no deployment, live role changes or Jira closure.
