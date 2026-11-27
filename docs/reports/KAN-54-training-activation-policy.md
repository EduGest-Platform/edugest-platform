# KAN-54 — Training activation decision / Decisión de activación formativa

27/11/2026 · Owner Elizabeth · Reviewer Anas · PO_ACCEPTED (functional scope); CODE_PRESENT_NOT_RUN for the new teacher regression; BLOCKED on coordination implementation and acceptance evidence. Prior accepted KAN-123 / #247: publication and cohort assignment are distinct; a teacher authorized in a cohort may publish for its program. This decision preserves that publication authority.

## ES — Decisión funcional aprobada por PO (27/11/2026)

Para el MVP, la habilitación formativa se realiza por cohorte: publicar un marco de competencias versionado del programa, asignarlo explícitamente a la cohorte y publicar actividades mediante su flujo propio.

- Responsable de la asignación: **docente o coordinación**, con autorización efectiva sobre la cohorte. No se requieren ambas aprobaciones.
- La publicación y edición de marcos conservan la autoridad existente de KAN-123. La autorización de coordinación se limita a asignar una versión ya publicada; no implica acceso a evaluaciones individuales, edición/publicación de marcos ni otros permisos docentes.
- Publicar una nueva versión no reasigna automáticamente las cohortes. Una versión archivada sigue disponible para las cohortes vinculadas; no se asigna de nuevo. Se conserva el histórico de evaluaciones.
- Registrar actor, fecha, versión anterior/nueva y auditoría. Denegar por defecto acciones fuera de ámbito.
- Las actividades mantienen su flujo independiente; no se introduce un bloqueo general por ausencia de marco.
- Sin interruptor global ni nueva entidad de plan formativo en el MVP. Cualquier ampliación requiere decisión de alcance. No cambiar catálogo público ni matrícula.

### Criterios de historia y evidencia

| Criterio | Evidencia integrada | Brecha |
|---|---|---|
| Docente habilita formación en su cohorte | #67, #130/#205–209, #269, #247; regresión de asignación en este PR | CI y demo de aceptación |
| Coordinación habilita formación en su ámbito | Decisión PO del 27/11 | No implementado: el endpoint de asignación exige `competencies.configure`; coordinación solo posee `competencies.aggregate` en el dominio de competencias |
| Aislamiento por rol y ámbito | test_competencies.py: test_teacher_of_another_cohort_gets_403; #141; prueba de denegación en este PR | Añadir pruebas positivas y negativas de coordinación tras implementar permiso específico |
| Autor, fecha y estado | CompetencyFramework.created_by/created_at/published_at/estado, CohortCompetencyFramework.assigned_by/assigned_at; eventos de creación, edición, publicación y asignación | No confundir estado del marco con estado del plan formativo |
| Modelo docente/programa/cohorte | catalog/models.py, identity/models.py, learning/team_router.py, docs/data/schema-reference.md | No añadir entidad Asignatura ni plan global para MVP |

### Casos de aceptación

1. Docente o coordinación con ámbito asigna versión publicada del mismo programa; actor/fecha/versión verificables en DB y auditoría.
2. Docente/coordinación sin ámbito, captación/coder o anónimo no pueden activar; 403/401; sin mutación ni evento de éxito.
3. Publicar nueva versión no sustituye automáticamente la asignada; reasignación explícita conserva histórico.
4. Marco borrador/archivado o de otro programa no puede asignarse (409).
5. Coordinación no adquiere permisos de evaluación individual ni de edición/publicación de marcos; probar autorización separada en backend y disponibilidad de la acción en la UI correspondiente.
6. Demostrar recorrido por cohorte con datos sintéticos, actividades independientes y revisión cruzada.

### Implementación pendiente

La regresión de este PR refleja el comportamiento actual: coordinación recibe 403. No se considera el resultado final aceptado de KAN-54. Implementar una autorización de asignación específica y acotada (por ejemplo `competencies.assign`), sin conceder `competencies.configure` ni `competencies.read` a coordinación; verificar cómo seleccionar las versiones publicadas sin exponer datos individuales. Adaptar las pruebas y la UI, verificar la matriz RBAC, CI/E2E y revisión cruzada. No modificar permisos reales, desplegar ni cerrar la historia en este cambio documental.

Evidencia histórica: [#247](https://github.com/EduGest-Platform/edugest-platform/pull/247), [#269](https://github.com/EduGest-Platform/edugest-platform/pull/269), [CI #271](https://github.com/EduGest-Platform/edugest-platform/actions/runs/46032355814) y [E2E #271](https://github.com/EduGest-Platform/edugest-platform/actions/runs/46032355812). No nueva ejecución local. Los cuatro hijos Jira están finalizados según la reconciliación previa; ello no acredita el DoD de la historia.

## EN — PO-approved functional decision (2026-11-27)

MVP training enablement is cohort-specific: publish a versioned program competency framework, explicitly assign it to a cohort, and publish activities through their independent existing workflow. **Either an authorized teacher or coordinator** may perform the assignment within their effective cohort scope; no joint approval is required. Preserve KAN-123's existing framework-edit/publication authority. Coordination's new responsibility is assignment of an already published version only, not individual assessments or additional teaching privileges.

Publication never automatically changes existing cohort assignments. Preserve archived versions for existing links, assessment history, actor/time and previous/new version audit. Reject out-of-scope actions by default, anonymous requests and draft, archived or foreign-program assignments. No global plan switch, new plan entity or blanket activity block in the MVP. Preserve public admission catalogue and enrollment behavior.

**Implementation gap:** the current assignment endpoint requires `competencies.configure`; coordination only has `competencies.aggregate` in this domain. The regression's current coordinator 403 documents the baseline, not the approved target. Implement a narrowly scoped assignment permission (e.g. `competencies.assign`), without granting broader configuration or individual-read permissions. Verify the published-version selection path, backend authorization, positive/negative coordinator regressions, audit, applicable UI, CI/E2E and synthetic demo. Historical CI is not fresh runtime evidence. The functional scope is accepted; KAN-54 remains open pending implementation and independent review. No deployment, live role changes or Jira closure.
