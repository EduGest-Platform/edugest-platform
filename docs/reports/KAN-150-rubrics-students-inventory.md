# KAN-150 — Rubrics and students logic inventory / Inventario de lógica de rúbricas y alumnado

**Status / Estado:** `CODE_PRESENT_NOT_RUN` for the local academic views; this document records a source inventory, not a certification of runtime behavior. Prepared 2026-11-22 from `dev` at `310f766d4754e28b90cb91558281ef9593d31ff7`. Jira KAN-150 remains pending human review.

## ES — Especificación

### Alcance

Inventariar la lógica local reutilizable de `src/gistar/views/Rubrics.tsx` y `src/gistar/views/Students.tsx`, junto con sus acciones, dominio, tipos y pruebas. Identificar qué puede conservarse, adaptarse o debe tratarse solo como demo al conectar la UI académica con la API publicada. El cambio entrega documentación bilingüe; no modifica frontend, API, contrato, base de datos ni pruebas de aplicación.

### Criterios de aceptación

1. El inventario cita componentes, funciones, tipos, pruebas y endpoints con rutas y nombres precisos.
2. Cada elemento se clasifica como **reutilizable**, **adaptable** o **solo demo**, justificando la decisión frente al estado local y al contrato de API.
3. Se documentan los límites de seguridad, persistencia, versionado e historial; no se presenta `localStorage` ni la identidad de demo como backend funcional.
4. La documentación incluye riesgos y un plan reproducible de comprobación TypeScript, Vitest y build. Pytest queda condicionado a una PostgreSQL de pruebas aislada y desechable.
5. Solo se cambia documentación; las comprobaciones informan resultados realmente ejecutados, sin cerrar KAN-150 ni KAN-57.

### Dependencias y contexto verificados

- KAN-150 (Idea) nombra como dependencia `PF2-EDU-01`; la búsqueda Jira identifica KAN-54, “Cursos, cohortes y activación por docentes autorizados”, también en Idea al 2026-11-22. Es una dependencia declarada, no un vínculo Jira formal verificado.
- Padre KAN-57 está En curso. Su alcance requiere árbol por curso/cohorte, niveles 1–3 y evaluaciones con historial.
- La parte de framework/seed está en API (PR #67 y #78, referenciadas en el comentario de KAN-57). La UI académica frontend sigue en el ámbito de KAN-186. Los endpoints actuales cubren competencias y evaluaciones, pero no rúbricas, tareas, entregas ni revisiones completas.
- No se encontró PR ni rama existente de KAN-150 en las búsquedas GitHub por clave. La rama de trabajo parte del `dev` publicado en `310f766d4754e28b90cb91558281ef9593d31ff7`.

### Riesgos

- Los componentes académicos locales usan `useGistar` y estado de demo persistido localmente; trasladarlos sin cambiar el origen de datos puede aparentar persistencia y autorización que no existen.
- Las reglas y tipos de rúbrica local (incluidos criterios, pesos y revisiones) no tienen una entidad/endpoint equivalente en la API actual; no mapearlos a evaluaciones de competencia sin definir el contrato.
- `nominalCohorts` y los nombres/roles `DEMO_USER` no son controles de acceso. La UI conectada debe obtener ámbitos y permisos del backend.
- `effectiveCompetencies` representa herencia y exclusiones locales; la API usa una versión de framework asignada a cohorte. Un mapeo directo puede mezclar competencias/versiones.
- Las métricas locales y fixtures sintéticos prueban reglas en memoria, no persistencia, historial real ni aislamiento de ámbito.

### Plan de verificación

- `pnpm exec tsc --noEmit -p tsconfig.json`
- `pnpm test` (Vitest)
- `pnpm build`
- Pytest de API: no ejecutar sin confirmar que `api/tests/conftest.py` provisiona una PostgreSQL aislada y desechable; no usar base compartida.
- Inspección de `git diff --check` y de la lista de archivos para confirmar que solo se añade este documento.

### Resultado ejecutado (2026-11-22)

- `pnpm exec tsc --noEmit -p tsconfig.json`: **PASS**.
- `pnpm test` (Vitest): **PASS**, 6 archivos / 53 pruebas.
- `pnpm build`: **PASS**, Vite 8.0.5 generó `dist/`.
- Instalación fijada por `pnpm-lock.yaml` completada en el entorno para ejecutar estas comprobaciones. Pytest no ejecutado: no se necesitó para el inventario y no se estableció una PostgreSQL desechable.

## EN — Specification

### Scope

Inventory reusable local logic from `src/gistar/views/Rubrics.tsx` and `src/gistar/views/Students.tsx`, including their actions, domain helpers, types, and tests. Classify what can be retained, adapted, or treated as demo-only when connecting academic UI to the published API. Deliver bilingual documentation only; do not change frontend, API, contract, database, or application tests.

### Acceptance criteria

1. The inventory cites components, functions, types, tests, and endpoints by exact path and name.
2. Each item is classified as **reusable**, **adaptable**, or **demo-only**, with reasoning grounded in local behavior and the API contract.
3. The document records persistence, authorization, versioning, and history limits; it does not present `localStorage` or demo identity as a working backend.
4. It includes risks and a reproducible TypeScript, Vitest, and build verification plan. Pytest is conditional on an isolated, disposable PostgreSQL test database.
5. Only documentation changes; verification reports actual results, without closing KAN-150 or KAN-57.

### Verified dependencies and context

- KAN-150 (Idea) names `PF2-EDU-01` as a dependency; Jira search resolves it to KAN-54, “Courses, cohorts and activation by authorized teachers,” also in Idea on 2026-11-22. This is a declared dependency, not a verified Jira issue link.
- Parent KAN-57 is In Progress. Its scope requires course/cohort trees, levels 1–3, and assessments with history.
- Framework/seed work exists in the API (PRs #67 and #78, cited in the KAN-57 comment). Frontend academic UI remains in KAN-186. Current endpoints cover competencies and assessments, but not full rubrics, tasks, deliveries, or reviews.
- GitHub searches by KAN-150 found no existing PR or branch. The work branch starts from published `dev` at `310f766d4754e28b90cb91558281ef9593d31ff7`.

### Risks

- The local academic views use `useGistar` and locally persisted demo state; connecting them without replacing the data source can imply persistence and authorization that do not exist.
- Local rubric rules and types (criteria, weights, and reviews included) have no equivalent entity/endpoint in the current API. Do not map them to competency assessments without defining the contract.
- `nominalCohorts` and `DEMO_USER` roles are not access controls. Connected UI must consume backend-authorized scopes and permissions.
- `effectiveCompetencies` models local inheritance and exclusions; the API uses a cohort-assigned framework version. A direct mapping may mix competencies or versions.
- Local metrics and synthetic fixtures test in-memory rules, not persistence, real history, or scope isolation.

### Verification plan

- `pnpm exec tsc --noEmit -p tsconfig.json`
- `pnpm test` (Vitest)
- `pnpm build`
- API pytest: do not run unless `api/tests/conftest.py` is confirmed to provision an isolated, disposable PostgreSQL database; never use a shared database.
- Inspect `git diff --check` and changed paths to confirm this document is the only addition.

### Executed results (2026-11-22)

- `pnpm exec tsc --noEmit -p tsconfig.json`: **PASS**.
- `pnpm test` (Vitest): **PASS**, 6 files / 53 tests.
- `pnpm build`: **PASS**, Vite 8.0.5 generated `dist/`.
- Dependencies pinned by `pnpm-lock.yaml` were installed in this environment for these checks. Pytest was not run: it was not needed for this inventory, and no disposable PostgreSQL instance was established.

## ES — Inventario de componentes y lógica

| Elemento | Clasificación | Evidencia y decisión |
|---|---|---|
| `Rubrics` (`src/gistar/views/Rubrics.tsx:11`) | **Adaptable** | Lista tareas/rúbricas, selecciona cohorte y ofrece borrador, publicación, duplicado y archivo. Reutilizar estructura/interacciones; sustituir `useGistar` y el modelo local. La API no ofrece CRUD de rúbricas. |
| `RubricEditor` / `emptyCrit` (`Rubrics.tsx:133,135`) | **Adaptable** | Formularios de criterios, pesos, competencias, reordenado y duplicación. Validación de pesos es reusable como regla UI, pero campos/guardado/historial deben esperar contrato de rúbrica y pruebas de servidor. |
| `StudentList` (`src/gistar/views/Students.tsx:6`) | **Adaptable** | Tabla de alumnado, cohortes, asistencia y progreso; puede conservarse como patrón de pantalla. Reemplazar selección de cohorte/coders y cálculos locales por datos API con scope. |
| `validateRubric` (`src/gistar/actions.ts:109`) | **Reutilizable** | Regla pura: al menos un criterio con nombre y pesos todos presentes o ausentes sumando 100. Apta para validación de formulario; API debe volver a validar cuando exista contrato. |
| `saveRubricDraft`, `publishRubric`, `archiveRubric` (`actions.ts:120,137,147`) | **Solo demo** | Mutan `GistarData` en memoria: asignan versiones, archivan anteriores y cambian `tarea.rubrica_id`. No tienen transacción, concurrencia ni persistencia. Usar solo como referencia de comportamiento. |
| `applyReview` (`actions.ts:14`) | **Solo demo** | Crea revisión/evaluaciones locales, usa `USR-DOC` por defecto y marca `origen: 'demo'`. No equivale al endpoint que registra evaluación de competencia. |
| `addCompetency`, `editCompetency`, `moveCompetency` (`actions.ts:82,94,99`) | **Adaptable** | Reglas locales de catálogo, código y orden. La API administra estas operaciones mediante frameworks versionados y autoriza en servidor; conservar solo UX/validaciones útiles tras alinear con las operaciones API. |
| `nominalCohorts` / `DEMO_USER` (`src/gistar/domain.ts:13,41`) | **Solo demo** | Restringe cohortes usando ids/roles fijos del fixture. Nunca portar como autorización. |
| `effectiveCompetencies` (`domain.ts:66`) | **Adaptable** | Resuelve catálogo por programa/cohorte con exclusiones heredadas. La API sirve el framework publicado asignado a cohorte; consultar esa respuesta en vez de recalcular herencia local. |
| `cohortCoders`, `activeTasks` (`domain.ts:51,149`) | **Adaptable** | Filtros puros útiles si los datos API se normalizan; hoy dependen de `GistarData`, estados locales y `Tarea` mock. |
| `evalIndex`, `levelAt`, `attendanceSummary` (`domain.ts:104,117,166`) | **Adaptable** | Agregaciones puras de historial publicado, corte temporal y ausencia de datos. Pueden orientar presentación si respetan historial/API y scope; su entrada local no es persistida ni autorizada. |

## EN — Component and logic inventory

| Item | Classification | Evidence and decision |
|---|---|---|
| `Rubrics` in `src/gistar/views/Rubrics.tsx` | **Adaptable** | Lists tasks/rubrics, selects a cohort, and offers draft, publish, duplicate, and archive flows. Reuse layout/interactions; replace `useGistar` and the local model. The API has no rubric CRUD. |
| `RubricEditor` and `emptyCrit` in `Rubrics.tsx` | **Adaptable** | Forms for criteria, weights, competencies, reordering, and duplication. Weight validation is reusable as a UI rule, but fields, saves, and history must wait for a rubric contract and server tests. |
| `StudentList` in `src/gistar/views/Students.tsx` | **Adaptable** | Student table, cohort selector, attendance, and progress can inform a screen pattern. Replace cohort/coder selection and local calculations with scoped API data. |
| `validateRubric` (`src/gistar/actions.ts`) | **Reusable** | Pure rule: at least one named criterion; weights must be all present or all absent, and weighted criteria total 100. Suitable for form validation; the API must validate again once a contract exists. |
| `saveRubricDraft`, `publishRubric`, `archiveRubric` (`actions.ts`) | **Demo-only** | Mutate in-memory `GistarData`: allocate versions, archive prior versions, and update `tarea.rubrica_id`. No transaction, concurrency handling, or persistence. Use only as behavioral reference. |
| `applyReview` (`actions.ts`) | **Demo-only** | Creates local reviews/assessments, defaults to `USR-DOC`, and sets `origen: 'demo'`. It is not equivalent to the API endpoint for competency assessments. |
| `addCompetency`, `editCompetency`, `moveCompetency` (`actions.ts`) | **Adaptable** | Local catalog, code, and ordering rules. The API manages these through versioned frameworks with server authorization; retain only useful UX/validation after matching API operations. |
| `nominalCohorts` and `DEMO_USER` (`src/gistar/domain.ts`) | **Demo-only** | Filters cohorts using fixed fixture ids/roles. Never port as authorization. |
| `effectiveCompetencies` (`domain.ts`) | **Adaptable** | Resolves program/cohort catalogs with local inherited exclusions. The API serves the published framework assigned to a cohort; consume that response instead of recalculating inheritance locally. |
| `cohortCoders`, `activeTasks` (`domain.ts`) | **Adaptable** | Pure filters could be useful after API data normalization; currently depend on `GistarData`, local states, and mock `Tarea`. |
| `evalIndex`, `levelAt`, `attendanceSummary` (`domain.ts`) | **Adaptable** | Pure aggregations over published history, a date cutoff, and missing values. They can inform presentation if API history and scope are preserved; local inputs are neither persisted nor authorized. |

## ES — Tipos, pruebas y contrato API

- `src/gistar/types.ts`: `Competencia` y `Coder` son conceptos aprovechables, pero no DTOs API. `Criterio`, `Rubrica`, `Tarea`, `Revision`, `Evaluacion` y `GistarData` modelan el demo local y se clasifican **solo demo** hasta contrato de rúbricas/entregas/revisiones.
- `src/gistar/__tests__/flows.test.ts`, sección “rubric → review → draft → publish → history”: prueba versionado local, métricas que ignoran borradores e historial conservado. Es evidencia de regla en memoria; adaptar casos a pruebas API una vez disponible el flujo de rúbricas.
- `src/gistar/__tests__/migrate.test.ts`: protege migración del seed v1→v2, niveles históricos y catálogos locales; mantener como regresión de demo, no como prueba de persistencia API.
- `src/gistar/__tests__/data-source.test.ts`: confirma que estas vistas no están en `API_VIEWS` y quedan en origen `local` en modo API. Revisar al integrar.
- `api/tests/test_competencies.py`: ya cubre creación/publicación/versionado de framework, asignación a cohorte, historial de evaluación y 403/409; no cubre rúbricas, tareas o revisiones.
- API vigente: `api/app/modules/competencies/router.py` expone `GET/POST /programs/{program_id}/competency-frameworks`, `PUT /competency-frameworks/{framework_id}/competencies`, `POST .../publish`, `GET /cohorts/{cohort_id}/competencies`, `PUT /cohorts/{cohort_id}/competency-framework` y `GET/POST /enrollments/{enrollment_id}/assessments`.
- `api/app/modules/competencies/schemas.py` define `FrameworkWrite`, `CompetencyWrite`, `AssessmentWrite`, `CurrentLevel` e historial `EnrollmentAssessments`. `service.py` controla scope, versión publicada de cohorte y auditoría. No hay endpoint de `Rubrica`, `Tarea`, `Entrega` o `Revision` en el router.

## EN — Types, tests, and API contract

- `src/gistar/types.ts:41,53`: `Competencia` and `Coder` are reusable concepts, but not API DTOs. `Criterio`, `Rubrica`, `Tarea`, `Revision`, `Evaluacion`, and `GistarData` (`types.ts:83-150,265`) describe the local demo and are **demo-only** until a rubric/delivery/review contract exists.
- `src/gistar/__tests__/flows.test.ts:41-73`, section “rubric → review → draft → publish → history”: tests local versioning, drafts excluded from metrics, and preserved history. This is in-memory rule evidence; adapt cases into API tests when a rubric flow exists.
- `src/gistar/__tests__/migrate.test.ts:7-35`: protects v1→v2 seed migration, historical levels, and local catalogs; retain as demo regression coverage, not API persistence coverage.
- `src/gistar/__tests__/data-source.test.ts:8-30`: confirms these views are not in `API_VIEWS` and use the `local` source in API mode. Revisit during integration.
- `api/tests/test_competencies.py`: already covers framework creation/publication/versioning, cohort assignment, assessment history, and 403/409; it does not cover rubrics, tasks, or reviews.
- Current API: `api/app/modules/competencies/router.py` exposes `GET/POST /programs/{program_id}/competency-frameworks`, `PUT /competency-frameworks/{framework_id}/competencies`, `POST .../publish`, `GET /cohorts/{cohort_id}/competencies`, `PUT /cohorts/{cohort_id}/competency-framework`, and `GET/POST /enrollments/{enrollment_id}/assessments`.
- `api/app/modules/competencies/schemas.py` defines `FrameworkWrite`, `CompetencyWrite`, `AssessmentWrite`, `CurrentLevel`, and history via `EnrollmentAssessments`. `service.py` enforces scope, the cohort's published framework, and audit logging. The router has no `Rubrica`, `Tarea`, `Entrega`, or `Revision` endpoint.
