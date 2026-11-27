# KAN-54 — Training activation decision / Decisión de activación formativa

27/11/2026 · Owner Elizabeth · Reviewer Anas · PROPOSED (not an approved decision). Prior accepted KAN-123 / #247: a published framework and a cohort assignment are distinct; a teacher authorized in a cohort may publish for its program. This proposal does not change that policy.

## ES — Criterios de historia y evidencia

| Criterio | Evidencia integrada | Brecha |
|---|---|---|
| Docente habilita formación en su cohorte | #67 competencias; #130/#205–209 directorio/panel; #269 UI de edición y evaluación; #247 definición | Activación global de plan no tiene operación acreditada |
| Docente ajeno recibe 403 | test_competencies.py: test_teacher_of_another_cohort_gets_403; #141 revocación de ámbito | Añadir prueba directa de asignación y auditoría |
| Autor, fecha y estado | CompetencyFramework.created_by/created_at/published_at/estado, CohortCompetencyFramework.assigned_by/assigned_at; eventos de creación, edición, publicación y asignación | No confundir estado del marco con estado de plan formativo |
| Modelo docente/programa/cohorte | catalog/models.py, identity/models.py, learning/team_router.py, docs/data/schema-reference.md | No añadir entidad Asignatura sin necesidad funcional |

### Decisión recomendada (requiere PO)
Para MVP, habilitar formación = configurar y publicar el marco versionado del programa, asignarlo explícitamente a una cohorte autorizada y publicar las actividades de esa cohorte por su flujo propio. No introducir interruptor global ni activación automática de todas las cohortes. Una versión archivada sigue disponible para las cohortes ya vinculadas; no se asigna a otras. No modificar el catálogo público de admisión ni la matrícula.

Alternativa si Melissa/PO exige plan global: definir plan como entidad versionada, estado borrador/publicado/archivado y activación separada por cohorte; documentar autoridad de publicación, estado previo, rollback/archivo, autorización, efecto sobre actividades existentes e historial. No implementar esta alternativa ni ampliar alcance sin aceptación y capacidad.

### Casos de aceptación
1. Docente con ámbito asigna versión publicada del mismo programa a su cohorte; actor/fecha/estado verificables en DB y auditoría.
2. Docente sin ámbito, captación/coder o anónimo no pueden activar; 403/401; no mutación ni evento de éxito.
3. Publicar nueva versión no sustituye automáticamente la asignada; reasignación explícita conserva historial de evaluaciones.
4. Marco borrador/archivado o ajeno no puede asignarse (409).
5. Si se aprueba MVP sin plan global, demostrar actividades y competencias por cohorte en demo sintética y registrar aceptación. Si plan global obligatorio, mantener KAN-54 abierta hasta implementación, contrato, migración y pruebas.

Evidencia remota observada: [#247](https://github.com/EduGest-Platform/edugest-platform/pull/247), [#269](https://github.com/EduGest-Platform/edugest-platform/pull/269), [CI #271](https://github.com/EduGest-Platform/edugest-platform/actions/runs/46032355814) y [E2E #271](https://github.com/EduGest-Platform/edugest-platform/actions/runs/46032355812) PASS históricos; no nueva ejecución local. Los cuatro hijos Jira están finalizados, no la historia. El PR propone decisión y refuerza evidencia de la semántica existente; no cambia permisos ni contrato.

## EN
For MVP, recommend explicit cohort-level enablement using the existing published competency framework, cohort assignment and separate activity publication. Preserve KAN-123's accepted publication authority, version history and scope. No global training-plan switch or automatic cohort updates. If a global plan is required, obtain PO acceptance and design an explicit versioned plan, state/authorization/audit contract and migration before implementation. The five acceptance cases above distinguish actual activation from publication, enforce actor/time/status and negative scope, and preserve previous evaluations. Historical CI is evidence, not fresh runtime certification. KAN-54 remains open until the PO decides and Anas reviews; the alternative is not implemented.
