# KAN-169 — UI integration / Integración UI

## ES

Implementación: Yohanna. Tarea asignada a Anas; único revisor solicitado: Anasfady. Deadline Jira: **26/11/2026**. Incremento del 24/11/2026.

Conecta el chat documental a /assistant/ask, sin fallback a respuestas locales. Muestra citas, versión, vigencia, método de recuperación y abstención. Las respuestas se renderizan como texto y el historial permanece solo en memoria (diez intercambios); limpiar cancela e invalida respuestas tardías.

## EN

Implementation: Yohanna. Jira assignee: Anas. Sole requested reviewer: Anasfady.

Connects document chat to the existing extractive backend with scoped citations, source validity, retrieval method and explicit abstention. No mock fallback or generated-answer claim. Renders source content as text; keeps only ten exchanges in memory and invalidates pending responses when cleared or unmounted.

## Validation / Validación

PASS: TypeScript, 87 frontend tests on the combined #130/#131 tree, production build and diff checks. Presentation regressions cover citation metadata, text escaping, abstention and missing-citation warnings.

## Limits / Límites

Based on PR #131 to preserve the shared screen registry. Merge #130 then #131, then retarget this PR to dev. Live browser/backend flow not run locally. No assistant tool execution or free-form LLM generation. / Recorrido real no ejecutado localmente; solo consulta documental extractiva.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
