# KAN-199 — Reproducible metric scenarios / Escenarios reproducibles de medición

## Dates / Fechas

KAN-199 deadline **30/11/2026** (not overdue on 20/11). Parent **KAN-69 deadline 17/11/2026 — overdue**. These are Jira due dates, not acceptance or changed commitments. Owner Yohanna; review Elizabeth with David for evidence semantics. No Jira mutation.

## ES

Runner CLI sobre `metrics.evaluate`, sin duplicar la fórmula ni leer/escribir PostgreSQL. Recibe un JSON inspeccionable de ocurrencias y un catálogo explícito, y produce `report.json`/`summary.csv` deterministas con hash SHA-256 de la entrada. No imprime filas, motivos o credenciales. Errores salen con código 2 y un mensaje genérico, sin copiar la entrada.

Este incremento ejecuta **escenarios hipotéticos sintéticos**, no mide el ahorro del producto. Los ejemplos generan 100 casos y 200 tareas con tiempos ficticios de 10/20 minutos por ocurrencia. El escenario mixto declara 150 completados hipotéticos; no deriva esos completados de las evaluaciones o recordatorios integrados. No exporta el seed #78 ni afirma que cien candidaturas sean cien casos con tareas elegibles.

Contrato de entrada estricto: schema_version 1, synthetic_only true, scenario_id técnico con prefijo synthetic-, catálogo con version, unit=per_task_occurrence, approval=hypothetical_not_approved y manual_minutes; listas occurrences/evidence. Cada ocurrencia declara application_id, task_id, task_type, eligible, automated y evidence_id. Los comprobantes hipotéticos declaran id, kind=hypothetical_completion y la misma candidatura/tarea/tipo. No se aceptan claves desconocidas, objetos JSON con claves duplicadas, NaN/Infinity, evidencia faltante/duplicada/no usada, identidad no sintética o recibos usados en otra tarea. Límite de entrada 2 MB y 10 000 filas/lista.

La evidencia debe corresponder exactamente a la ocurrencia y tener identificador único. Se rechazan tipos evaluation, human_review, simulated_reminder y cualquier tipo distinto de hypothetical_completion: declarar una evaluación como automated no la convierte en trabajo completado. El formato no autentica hechos reales: producción siempre figura como NO autenticada y el estado del informe dice HYPOTHETICAL_SCENARIO_NOT_MEASURED_SAVINGS. La aprobación de cliente sigue PENDING. No se añade un adaptador de eventos reales ni se modifica el criterio canónico de elegibilidad.

El evaluador existente conserva allow-list de preselección, entrevistas excluidas aunque se aporten minutos, números finitos/no negativos y denominador cero indefinido. CSV muestra `undefined`; JSON mantiene null. No hay catálogo aprobado por defecto ni conversión persona/lote. El catálogo ficticio de ejemplos no debe usarse como tiempos del cliente.

## EN

CLI wrapper around the existing evaluator, not a new formula or database adapter. Validated inspectable scenario JSON produces deterministic aggregate JSON/CSV with an input digest. Strict schema, synthetic identifiers, explicit hypothetical per-task catalogue and payload-bound unique receipts prevent accidental evidence reuse or counting evaluations/reminders as completions. Duplicate JSON keys and non-finite constants fail closed before outputs are created.

This is synthetic scenario execution only. The examples declare hypothetical completions; they are NOT exports or observed outcomes of the integrated engine/seed. Every report explicitly marks production evidence unauthenticated, client approval pending and savings unmeasured. Completing KAN-69 still needs source authentication, accepted units/minute catalogue and eligible real execution evidence. No new dependencies, API, DB, scheduler, seed, roles, Jira changes or completion claims.

## Reproduce / Reproducir

Run from repository root, choosing an output folder outside tracked source:

```text
python evals/automation/metric_examples.py --out <output>/inputs
python evals/automation/run_metrics.py --input <output>/inputs/synthetic-manual-only-100.json --out <output>/manual
python evals/automation/run_metrics.py --input <output>/inputs/synthetic-mixed-100.json --out <output>/mixed
python -m unittest discover -s evals/automation -v
```

Compare report.json and summary.csv bytes when rerunning the same input. The same metrics from different input formatting may have a different input hash, intentionally. The runner never overwrites its own input with an output file. Invalid inputs create neither report; filesystem errors can still require rerunning an interrupted write.

## Validation / Validación

Local: ruff PASS; **45 automation tests PASS** (12 new runner tests); both CLI examples actually generated. Known arithmetic: manual-only 0/3000 minutes; mixed 2000/3000, 66.67% under fictitious assumptions. Neither value is measured production savings or proof of client acceptance. Tests cover weighting, 100 eligible cases, noncompletion evidence, binding/reuse, scope exclusion, strict catalogue/schema/flags, invalid IDs/minutes, undefined results, deterministic artifacts and CLI failure without input echo. Current-head CI recorded in PR.

Generated example inputs and reports use explicit LF bytes on Windows and Linux, so their hashes and committed artifacts remain portable. / Entradas de ejemplo e informes usan LF explícito en Windows y Linux para conservar hashes y artefactos portables.
