# Publicación y activación académica / Academic publication and activation

El camino académico distingue la publicación por programa de la asignación por cohorte. La publicación del catálogo de admisión tiene su propio estado en la convocatoria.

The academic workflow separates publication by program from assignment by cohort. Admissions catalogue publication has its own status on the call.

| Operación / Operation | Resultado / Result | Evidencia / Evidence |
|---|---|---|
| Publicar un marco / Publish a framework | Congela el borrador del programa y archiva la versión publicada anterior. Las cohortes mantienen la versión que ya tienen asignada. / Freezes the program draft and archives the previous published version. Cohorts keep their assigned version. | `POST /competency-frameworks/{framework_id}/publish` |
| Asignar a una cohorte / Assign to a cohort | Vincula explícitamente el marco publicado del mismo programa a una cohorte. La escritura requiere permiso sobre esa cohorte y conserva persona y fecha. / Explicitly binds the same program's published framework to one cohort. The write requires permission on that cohort and records actor and time. | `PUT /cohorts/{cohort_id}/competency-framework` |
| Usar el marco activo / Use the active framework | La evaluación usa el marco asignado a la cohorte. Una nueva asignación cambia las competencias actuales y conserva las evaluaciones históricas. / Assessments use the cohort's assigned framework. A new assignment changes the current competencies and preserves assessment history. | `GET /cohorts/{cohort_id}/competencies` and `GET /enrollments/{enrollment_id}/assessments` |

**ES** — Para competencias, «activo» significa «asignado a la cohorte». La API vigente representa esa activación con el vínculo `CohortCompetencyFramework`. La publicación de actividades usa el estado de cada actividad y se verifica por separado. Un plan de formación con activación global queda pendiente de decisión funcional.

**EN** — For competencies, “active” means “assigned to the cohort”. The current API represents activation through the `CohortCompetencyFramework` link. Activity publication uses each activity's status and is verified separately. A training plan with global activation remains a product decision.

El [router](../../api/app/modules/competencies/router.py) y las [pruebas de competencias](../../api/tests/test_competencies.py) documentan el contrato vigente. / The router and competency tests document the current contract.
