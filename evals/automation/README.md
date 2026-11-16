# Offline automation foundation / Base de automatización offline

## ES — alcance y ejecución

KAN-53 / KAN-69; owner Yohanna; revisión pendiente de David (reglas) y Elizabeth (métrica/contrato).
Base inspeccionada: `dev`, `dd0ab0f146f86a6aa202c7c715d1d74ea71099b7`, 16/11/2026.

Desde la raíz, sin dependencias nuevas:

```sh
python -m unittest discover -s evals/automation -v
```

Estado: **VERIFIED_RUNNING solo para las 14 pruebas offline**. No es un motor integrado ni una medición del producto.

- `api/app/modules/automation/engine.py`: propone recordatorios simulados y revisión humana de faltantes/silencio. Política desactivada por defecto; ámbito por convocatoria; fechas con zona horaria; claves estables por convocatoria, candidatura, tarea, versión y acción.
- `metrics.py`: calcula cobertura por ocurrencias elegibles, con numerador, denominador, número de casos, fórmula aprobada y mínimo de 100 casos separados. Sin denominador devuelve `None`. Rechaza duplicados y automatizaciones sin referencia a evidencia. La existencia y veracidad de esa evidencia debe verificarse fuera del evaluador.
- `test_offline.py`: verifica límites temporales, aislamiento entre convocatorias, reintentos, tareas completadas, ausencia de exclusiones automáticas y protección de la métrica frente a duplicados. Los 100 casos se generan solo para probar el cálculo; no son el dataset unificado ni un resultado del 70 %.

Pendiente antes de integrar:

1. Elizabeth aprueba el catálogo, fórmula/unidad y política por convocatoria (EL1, KAN-69). Esta variante mide ocurrencias; no sustituye la propuesta anterior por tipos de tarea ni calcula ahorro de tiempo. No suma los 20/15/20 minutos por aspirante.
2. Elizabeth confirma los contratos F2 y la representación de tareas/ejecuciones. La entrada `Task` es un objeto interno, no un nuevo modelo de candidatura.
3. Añadir persistencia PostgreSQL, migración coordinada y restricción única para `Proposal.key`; transacción/outbox para concurrencia. Las claves estables **no** garantizan entrega idempotente sin ese adaptador. Cambiar versión permite nuevas propuestas y requiere revisión.
4. El adaptador debe comprobar rol/ámbito antes de leer tareas, excluir expedientes que hayan salido de preselección y auditar ejecuciones; nunca cambiar admisión. Los controles de ámbito del núcleo no sustituyen RBAC.
5. Conectar bandeja simulada, scheduler del backend existente y registros reales; después E2E y revisión cruzada. No hay correo, endpoints, scheduler ni migraciones en esta entrega.

No se modifican los PR abiertos #7/#8. No se han ejecutado Docker, PostgreSQL, la suite API completa ni pruebas web en esta entrega: no se cambian esos componentes.

## EN — scope and execution

KAN-53 / KAN-69; owner Yohanna; pending review by David (rules) and Elizabeth (metric/contract).
Inspected base: `dev`, `dd0ab0f146f86a6aa202c7c715d1d74ea71099b7`, 2026-11-16.
Run the command above from the repository root; no new dependencies.

Status: **VERIFIED_RUNNING for the 14 offline tests only**. This is neither an integrated engine nor a product measurement.

- The engine proposes simulated reminders and human review for missing requirements or elapsed response windows. Policies default to disabled; inputs are call scoped, timestamps require timezones, and operation keys are stable.
- The evaluator measures eligible task occurrences, reports numerator/denominator/case count, and keeps formula approval separate from the 100-case minimum. Zero denominator is unknown. Duplicate occurrences and automated rows without evidence references are rejected; evidence authenticity needs independent verification.
- The tests cover time boundaries, call isolation, retries, completed tasks, human-only outcomes and metric inflation. The 100 generated test cases are calculation fixtures, not the unified dataset or a measured 70% result.

Integration prerequisites:

1. Elizabeth approves the task inventory, formula/unit and call policy. Occurrence coverage does not replace task-type coverage or estimate time savings; do not add the 20/15/20-minute estimates per applicant.
2. Confirm F2 contracts and execution/task representation; `Task` is internal, not a duplicate application model.
3. Add coordinated PostgreSQL migration, unique operation keys and transactional outbox. Stable keys alone do not ensure concurrent delivery idempotency. New policy versions permit new proposals and need review.
4. The adapter must enforce backend role/scope permissions, exclude applications outside preselection and audit execution. Core scope validation is not RBAC. Never change admission outcomes.
5. Connect the simulated inbox, existing-backend scheduler and real execution records, then run E2E and cross-review. No email delivery, endpoints, scheduler or migrations are included.

Open PRs #7/#8 are unchanged. Docker, PostgreSQL, the full API suite and web tests were not run for this isolated change; those components are unchanged.
