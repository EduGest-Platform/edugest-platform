# KAN-219 — Web CI evidence / Evidencia web en CI

## ES

Responsable: Yohanna. Único revisor solicitado: Anas. Deadline Jira: **25/11/2026**. Incremento del 24/11 sobre `dev@72262cd`, independiente de KAN-200/#127. Complementa la [evidencia API existente](KAN-219-api-ci-evidence.md).

El job `web` ejecuta los mismos tests de Vitest con sus reporteros normal y JUnit. El XML queda temporalmente en el runner; solo se publica `web-test-summary-<SHA>` durante **7 días**, con el mismo esquema JSON de API: commit, resultado del paso, estado y contadores. No se publica el XML ni se copian nombres de tests, rutas, mensajes, propiedades, stdout o trazas al artefacto/resumen. Los logs normales de Actions conservan su comportamiento previo.

El resumen usa una etiqueta cerrada `--suite web`; omitirla mantiene el comportamiento API. El SHA de Actions puede corresponder al merge sintético del PR. Los fallos originales siguen fallando el job. Si el paso no se ejecuta, falla o se interrumpe, el informe no acredita éxito aunque el XML tenga contadores positivos. Sin XML válido, informa contadores nulos. No se modifica `continue-on-error`, protecciones de rama, despliegues ni Jira.

**Verificación local ejecutada:** 80 tests de Vitest en 9 archivos pasaron con ambos reporteros; el resumen del JUnit real produjo 80 correctos y cero fallos/errores/omitidos. Las 15 pruebas de `scripts/ci/tests` pasaron (10 del resumen y 5 del backup); Ruff y `git diff --check` correctos. Los casos CLI cubren etiqueta web, éxito/fallo/omisión y rechazo de etiquetas arbitrarias. El informe local se generó sobre el árbol modificado desde ese commit base; no constituye evidencia de ejecución de Actions del futuro commit.

**Límites:** no se ha ejecutado el workflow de GitHub localmente ni esperado su CI. La evidencia publicada real necesita ejecución de Actions. Este resumen solo representa Vitest, no TypeScript, build, navegador, API, aceptación funcional ni configuración de checks obligatorios. El gate de integración pendiente descrito en el informe API no queda resuelto por este incremento.

## EN

Owner: Yohanna. Sole requested reviewer: Anas. Jira deadline: **2026-11-25**. November 24 increment from `dev@72262cd`, independent of KAN-200/#127; complements the [existing API evidence](KAN-219-api-ci-evidence.md).

The web job runs its existing Vitest suite with default and JUnit reporters. Raw XML remains temporary; only aggregate JSON is uploaded as `web-test-summary-<SHA>` for **7 days** using the existing API schema. It includes the checked commit (potentially a synthetic PR merge), step outcome, status and counts. Test identities, paths, messages, properties and captured output are not copied to the artifact or summary. Normal Actions logs are unchanged.

The restricted `--suite web` option labels the summary; the default remains API. Original test failures still fail the job. Failed, skipped or cancelled steps cannot become passing evidence; missing/invalid reports retain null counts. No branch protections, deployment or Jira changes occur.

**Local verification:** 80 Vitest tests across 9 files passed with both reporters; their real JUnit summarized to 80 passes and zero failures/errors/skips. All 15 CI helper tests passed (10 summary tests and 5 backup tests), together with Ruff and diff checks. CLI coverage includes web labeling, success/failure/skipped outcomes and rejection of arbitrary labels. This local run used the modified working tree based on the cited commit, not a GitHub Actions run for the future commit.

**Limits:** the GitHub workflow was not executed locally and CI was not awaited. Actual uploaded evidence requires an Actions run. Vitest counts do not certify type checking, build, browser/API flows, functional acceptance or required-check configuration. The integration gate noted in the API report remains separate.
