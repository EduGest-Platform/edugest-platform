# KAN-205 — Scenario results and limits / Resultados y límites de escenarios

KAN-205 deadline **30/11/2026** (not overdue on 20/11). Parent KAN-69 deadline **17/11/2026 — overdue / vencida**. Prepared 20/11 against runner commit `e5943dd` in #83. No deadline, assignment or Jira state is changed.

## ES — Qué resultado se publica

Se publican dos ejecuciones reales del runner sobre entradas **hipotéticas sintéticas**, no una medición real del producto. Los artefactos se han generado con el código de KAN-199; no se han rellenado cifras manualmente ni se ha usado información de personas. Esta distinción prevalece sobre las palabras «automated» o «saved» que conserva el contrato del evaluador.

| Scenario / Escenario | Cases / Casos | Eligible tasks / Tareas elegibles | Hypothetical completed / Completadas hipotéticas | Assumed baseline minutes / Minutos base supuestos | Hypothetical saved minutes / Minutos hipotéticos ahorrados | Ratio / Cociente |
|---|---:|---:|---:|---:|---:|---:|
| synthetic-manual-only-100 | 100 | 200 | 0 | 3000.0 | 0 | 0.00% |
| synthetic-mixed-100 | 100 | 200 | 150 | 3000.0 | 2000.0 | 66.67% |

**No se demuestra el objetivo del 70 %.** El 66,67 % corresponde a declarar hipotéticamente completas cien tareas de documentación y cincuenta de ejercicios; el 0 % corresponde a no declarar ninguna. La verdad del producto no se deduce de ninguno de esos escenarios. No afirmar tampoco que el producto tiene ahorro real cero: aquí no se ha medido.

### Supuestos explícitos

- Cien casos ficticios, dos ocurrencias elegibles por caso: documentación y ejercicios. No son cien filas extraídas de PostgreSQL ni certifican cien casos elegibles reales del seed #78.
- Catálogo synthetic-example-v1: 10 minutos para documentación, 20 para ejercicios, por ocurrencia; cifras ilustrativas, NO tiempos aceptados por Melissa o Elizabeth para producción. No se transforma persona en lote.
- Sustitución completa hipotética del trabajo manual: no se mide coste residual, revisión humana, tiempo observado o efecto causal. 150/200 tareas y 2000/3000 minutos son unidades diferentes: no informar 75 % de tareas como 75 % de ahorro temporal.
- Comprobantes hypothetical_completion vinculados a candidatura/tarea/tipo dentro del fichero. El runner comprueba estructura/consistencia, no autentica entregas o ejecución real. Evaluaciones, revisión humana y recordatorios simulados están excluidos como comprobantes de finalización.
- Todos los informes conservan client_approval=PENDING, production_evidence_authenticated=false y HYPOTHETICAL_SCENARIO_NOT_MEASURED_SAVINGS. No inferir aprobación ni autenticidad del hash.

### Para poder informar un resultado del producto

Elizabeth debe aceptar catálogo/unidad y delimitar con el cliente tareas elegibles. Se necesita una fuente verificable de trabajo completado, vínculo con ocurrencias únicas y periodo de observación, base manual comparable, coste residual cuando corresponda y cien casos realmente elegibles. Los registros de evaluación y la bandeja simulada integrados no bastan. Si faltan datos o el resultado está por debajo del objetivo, se informa así; no ajustar el escenario para fabricar un 70 %.

## EN — Meaning and limits

Two actual runner executions over declared hypothetical synthetic inputs are published, not measured product savings. The mixed scenario assumes 100 documentation and 50 exercise occurrences completed; manual-only assumes none. Illustrative per-occurrence minutes are 10/20, not an approved client catalogue. The weighted ratio is 2000/3000 = 66.67%, while the task-count fraction is 150/200 = 75%; they are different quantities.

Neither scenario proves the 70% objective or even establishes zero real savings. No database/seed extraction, actual completion authentication, observed manual/remaining effort, causal effect or real learner data is involved. Reports retain PENDING client approval, false production authentication and explicit unmeasured-scenario status. Input digests establish byte identity, not factual truth or policy approval.

Production reporting still needs accepted eligibility/catalogue/unit, authenticated completion sources, unique occurrences and period, comparable manual baseline, residual-cost treatment where appropriate and 100 genuinely eligible cases. Integrated evaluations, human reviews and simulated reminders cannot substitute for completed work. Do not tune examples to manufacture the target or mark KAN-69 complete.

## Artifacts / Artefactos

- [Manual-only JSON](KAN-205-scenarios/manual-report.json) / [CSV](KAN-205-scenarios/manual-summary.csv).
- [Mixed hypothetical JSON](KAN-205-scenarios/mixed-report.json) / [CSV](KAN-205-scenarios/mixed-summary.csv).
- [Runner contract and commands / Contrato y comandos](KAN-199-metric-runner.md).

Input SHA-256 / SHA-256 de entrada:

- `synthetic-manual-only-100`: `41d49e280368b7f46554d52162f4d8fd1db4e8b9bf2f4e96244d05f9afed95cf`
- `synthetic-mixed-100`: `8d4900e5b08099c92c51d374efa250b7bf9d4488421ad0a6fd97149a8064a42e`

## Reproduction and validation / Reproducción y validación

Use runner `e5943dd` (or verify compatible later code), generate inputs with metric_examples.py and run both commands from the KAN-199 report. Compare report.json and summary.csv bytes with these committed artifacts. Reformatting the input changes its byte hash even when calculated metrics remain equal.

Both CLIs executed locally; 45 automation tests PASS in KAN-199. Artifact byte equality, JSON/CSV agreement, source links and whitespace checked here. Current-head CI recorded in the PR. This PR adds only report/artifacts and is stacked on #83: integrate the runner first, retarget to dev and repeat checks. Elizabeth reviews interpretation/acceptance; David checks evidence boundaries. No Jira mutation, deployment, data migration or task-completion claim.

Inputs/reports regenerated with explicit LF bytes (runner e5943dd): the same example bytes and hashes are reproducible on Windows/Linux. / Entradas e informes regenerados con LF explícito para reproducibilidad de bytes/hashes en Windows/Linux.
