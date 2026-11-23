# KAN-219 — API CI evidence / Evidencia API en CI

## ES

Responsable: Yohanna. Revisor GitHub solicitado: **Anas**. Deadline Jira: **25/11/2026**, no vencido al 23/11. La propuesta 03/12 de la descripción no sustituye ese deadline. Incremento independiente sobre `dev@d3bdeb3`; los recorridos API de KAN-182/#99 ya están integrados.

### Qué aporta

El job `api` sigue ejecutando pytest sobre PostgreSQL sintético real, ahora con JUnit temporal en el runner. `scripts/ci/summarize_junit.py` extrae exclusivamente los totales y escribe una tabla en el resumen de Actions y un JSON descargable con versión de esquema, commit comprobado, resultado del paso, estado y contadores. El commit es `GITHUB_SHA`: en un PR puede ser el commit de merge de prueba, no el SHA de su rama.

El artefacto `api-test-summary-<SHA>` se conserva **7 días**. No contiene nombres de tests/personas, rutas, mensajes, trazas, propiedades, stdout ni stderr. El JUnit original no se sube. Los logs normales de Actions siguen sujetos a la política existente; este cambio no modifica su retención ni sustituye la revisión de logs de KAN-209.

### Fallos y límites

- Los fallos originales de pytest siguen fallando el job: no se añade `continue-on-error`.
- Si pytest falla, se cancela o no llega a ejecutarse, el resumen no declara éxito aunque el XML parcial tenga contadores sin fallos.
- Sin informe o con formato inválido se informa `unavailable`/`invalid` y contadores nulos: no se inventan cero fallos.
- Un informe vacío o completamente omitido tampoco se presenta como éxito. Fallos de preparación anteriores mantienen el job fallido; la carga del JSON exige que exista el archivo.
- Solo resume API pytest. No certifica las pruebas web, RAG, ML, navegador, despliegue o aceptación funcional.
- Comprobación de solo lectura el 23/11: `branches/dev/protection` devuelve `required_status_checks: null` y una revisión obligatoria; `rules/branches/dev` no devuelve reglas de checks requeridos. Por tanto, no hay evidencia de bloqueo de merge por CI en esa configuración. Este PR no modifica protecciones: configurar y verificar ese gate corresponde a responsables del repositorio y sigue pendiente para KAN-219.
- No actualiza Jira, no despliega ni ejecuta migraciones fuera del entorno desechable ya configurado en CI.

### Verificación

Local: `python -m unittest discover -s scripts/ci/tests -v` (**8 casos correctos**); Ruff de los scripts y `git diff --check` correctos. Los casos cubren conteo de suites hermanas sin doble suma, errores, estado del proceso, todo omitido, XML inválido/inconsistente, informe ausente y salida CLI sin textos privados. El job `automation` incorpora esas regresiones. PostgreSQL/pytest completo no se ejecutó localmente; su ejecución y el artefacto real se comprueban en CI antes de aceptar.

## EN

Owner: Yohanna. Sole requested GitHub reviewer: **Anas**. Jira deadline: **2026-11-25**, not overdue on November 23; the description's December 3 proposal is separate. Independent increment from `dev@d3bdeb3`, which already includes KAN-182/#99.

The existing API job still runs pytest against disposable synthetic PostgreSQL. It now creates temporary JUnit and publishes only aggregate evidence: schema version, checked commit, step outcome, status and integer counts. `GITHUB_SHA` identifies the tested commit, which may be a synthetic PR merge commit. The Actions summary displays totals; `api-test-summary-<SHA>` is downloadable for **7 days**. Original XML, test identities, paths, properties, messages, traces and captured output are never uploaded by this step. Existing Actions logs and their retention are unchanged.

Pytest failure remains blocking for the job. Interrupted/skipped steps, absent/invalid reports and empty/all-skipped suites never become passing evidence. Missing reports use null counts rather than fabricated zero failures. The summary step also fails closed and the upload requires an existing JSON file.

This is API evidence only, not proof of web/RAG/ML/browser/deployment success, required-check configuration or PO acceptance. Read-only GitHub API inspection on November 23 returned `required_status_checks: null`, one required approval and no effective required-status-check rules for dev. CI-based merge blocking is therefore not established by that configuration. Repository owners still need to configure/verify the gate; this PR changes no protection settings or final acceptance. No Jira update or external deployment/migration occurs.

Local: eight standard-library regression cases passed, together with Ruff and diff checks. CI's automation job runs those regressions; the API job validates actual pytest JUnit and artifact publication. Full local PostgreSQL tests were not run; record actual CI evidence before accepting.
