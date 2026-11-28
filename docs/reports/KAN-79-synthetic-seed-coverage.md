# KAN-79 · Cobertura del seed sintético / Synthetic seed coverage

**Base / Baseline:** `dev@67357d0`, 28/11/2026. **Responsable / Owner:** Yohanna. **Revisión / Reviewer:** Elizabeth.

## Ejecución verificada / Verified run

**ES** — Se ejecutaron `alembic upgrade head` y dos cargas normales con `python -m app.seed` en PostgreSQL 16 desechable. La segunda carga encontró los datos ya presentes. Las suites de integridad del seed base y académico pasaron **18 pruebas** en esa ejecución. La comprobación utilizó recuentos agregados de la primera carga, sin exportar expedientes ni credenciales.

**EN** — Ran `alembic upgrade head` and two standard `python -m app.seed` loads on disposable PostgreSQL 16. The second load found the fixtures already present. The base and academic seed integrity suites passed **18 tests**. The inventory used aggregate counts from the initial load.

| Criterio / Criterion | Observado / Observed | Límite / Limit |
| --- | --- | --- |
| Convocatorias, cohortes y perfiles / Calls, cohorts and profiles | 100 candidaturas en 2 convocatorias. 20 matrículas en 2 cohortes con datos académicos. Las fichas de demo cubren cinco roles internos y los estados aspirante y coder. / 100 applications across 2 calls. 20 enrollments across 2 cohorts with academic records. Demo accounts cover five staff roles plus applicant and learner states. | Aspirante y coder se derivan del ciclo de vida. / Applicant and learner are lifecycle states. |
| Estados y procedencia / Stages and origin | Ocho etapas persistidas. Las 100 candidaturas precargadas tienen origen `formulario`. / Eight persisted stages. All 100 seeded applications have the `formulario` origin. | Faltan ejemplos precargados de otros orígenes. La entrada manual se prueba por separado. / The baseline lacks seeded examples from other origins. Manual intake has separate coverage. |
| Asistencia y competencias / Attendance and competencies | 52 medias jornadas, 230 presencias, 6 faltas justificadas, 4 sin justificar y competencias C1–C10. / 52 half-days, 230 present records, 6 excused and 4 unexcused absences, and competencies C1–C10. | La carga base carece de sesiones de jornada completa. La suite académica verifica que una jornada completa preexistente se conserva al reejecutar la carga. / The baseline lacks full-day sessions. The academic suite checks preservation of an existing full-day session on rerun. |
| Analítica, métrica y ML / Analytics, metric and ML | La analítica consulta registros PostgreSQL. El evaluador del 70 % usa ocurrencias elegibles con catálogo explícito. El baseline de abandono usa sus propios escenarios sintéticos. / Analytics reads PostgreSQL records. The 70% evaluator needs eligible task occurrences and an explicit catalogue. Dropout evaluation uses separate synthetic scenarios. | Las 100 candidaturas precargadas solo acreditan volumen del seed. La alineación de variables, periodos y recuentos con los escenarios de ML queda por revisar. / The 100 seeded applications establish dataset size. Alignment of variables, periods and counts with ML scenarios is pending. |

## Reproducir / Reproduce

**ES** — En una base PostgreSQL desechable nueva, cargar el dataset dos veces y ejecutar las suites con `GISTAR_TEST_DATABASE_URL` dirigido exclusivamente a esa base de pruebas.

**EN** — On a fresh disposable PostgreSQL database, load the dataset twice and run the suites with `GISTAR_TEST_DATABASE_URL` pointing exclusively to that test database.

```sh
cd api
alembic upgrade head
python -m app.seed
python -m app.seed
python -m pytest tests/test_seed_base_integrity.py tests/test_seed_academic.py
```

**Pendiente / Pending:** acordar con Producto qué ejemplos adicionales deben pasar a la carga compartida y revisar la coherencia entre escenarios. / Agree which additional examples belong in the shared baseline and review cross-scenario consistency.

[Integridad del seed / Seed integrity](KAN-131-seed-base-integrity.md) · [Evaluador de automatización / Automation evaluator](../../evals/automation/README.md) · [Baseline ML](../../ml/README.md)
