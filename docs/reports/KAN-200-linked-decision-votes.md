# KAN-200 — Linked human vote evidence / Evidencia de votos humanos vinculados

## ES

Responsable: Yohanna. Único revisor solicitado: Anas. **Deadline Jira: 02/12/2026**. Base `dev@f4888cc`, inspeccionada el 24/11. Incremento independiente de #125 y #126.

### Problema y comportamiento

El quórum ya guarda cada voto en `SelectionApproval` y vincula todos los votos abiertos —incluidos los que quedan en minoría— a la decisión aplicada. La API mostraba esos votos mientras estaban pendientes, pero al cerrar la decisión dejaban de aparecer en la respuesta del historial. La metadata seguía en PostgreSQL, sin proyección en ese contrato.

Se añade `votes` a `SelectionDecisionOut`, tanto en el 201 de aplicación como en `GET /applications/{id}/selection-decisions`. Cada voto mantiene la misma proyección ya usada para pendientes: decisión propuesta, cohorte, motivo, nombre del actor y fecha. La consulta se limita a IDs de decisiones de la candidatura autorizada y a esa misma candidatura. La carga del historial agrupa todos sus votos con una consulta, sin consultar cada decisión por separado.

| Situación | Interpretación de `votes` |
|---|---|
| Dos personas coinciden | Se conservan los dos registros vinculados |
| Hay discrepancia y luego se alcanza quórum | También aparece el voto discrepante; no presentar la lista como unanimidad |
| Lista de espera seguida de admisión | Cada decisión conserva su propio grupo, sin reutilizar votos cerrados |
| Decisión antigua sin votos vinculados | Lista vacía: falta esa evidencia, no se inventan firmas a partir del actor final |
| Se cambia después la política de convocatoria | Los votos históricos no cambian; `quorum` de la respuesta sigue siendo la política **actual**, no la de aquella decisión |

Los nombres de actor se resuelven desde las cuentas actuales, igual que en la respuesta previa de votos pendientes; no son un snapshot inmutable de identidad, rol o nombre histórico. Este incremento no reconstruye quórums, requisitos, reglas ni puntuaciones de una fecha pasada. Los motivos siguen siendo texto operativo privado dentro del mismo ámbito; no se añaden a auditoría ni logs.

### Seguridad y límites

Se conservan las comprobaciones `selection.read`/`selection.decide` del servidor. No se monta una ruta nueva, no se concede acceso a captación/coders/docentes ni se cambia la lógica de decisión, matrícula o persistencia. No hace falta migración: se leen filas ya existentes. El campo es aditivo y tiene lista vacía por defecto; OpenAPI y cliente TypeScript están regenerados.

La evidencia de votos humanos no es un score de selección, resultado de automatización ni medición del 70 %. La matriz ética/aceptación PO y el alcance completo de KAN-200 siguen sujetos a revisión; no se actualiza Jira.

### Validación

Seis casos API cubren POST/historial, desacuerdo, política posterior, agrupación por decisión, legado sin votos y denegación de convocatoria ajena. Ruff y compilación Python correctos; **PostgreSQL/pytest no ejecutado localmente**. TypeScript, **80 tests frontend** y build correctos. Contrato regenerado, diff revisado. CI no esperado ni declarado correcto por petición del usuario.

## EN

Owner Yohanna; sole requested reviewer Anas. **Deadline 2026-12-02**, independent `dev@f4888cc` snapshot on November 24.

Selection approvals already persist and link to an applied decision, including outvoted records. Previously only pending votes were projected; after application, history omitted the linked records. The additive `SelectionDecisionOut.votes` now exposes their existing minimal pending-vote projection on both successful POST and history GET: proposed decision/cohort, operational reason, actor name and timestamp.

Queries bind both authorized application and decision IDs, loading/grouping a history's closed votes together. Waiting-list and later-admission groups remain separate. Disagreements are retained rather than implying unanimity. Legacy decisions without rows return an empty list, not invented approvals. Later policy changes do not rewrite votes; the response's `quorum` remains current policy, not reconstructed historical policy. Actor names resolve from current accounts as before, not immutable historical identity snapshots.

Existing scope/action checks and decision/enrollment writes are unchanged. No new route, permissions, migration, raw-audit exposure or logging of reasons. OpenAPI and the TypeScript client are regenerated. This is human-review evidence, not a score, automated decision or 70% metric; wider ethical/PO acceptance remains pending.

Six API regression cases cover applied/history output, disagreement, later policy change, separate rounds, missing legacy evidence and foreign-call denial. Local Ruff/Python compilation, TypeScript, 80 frontend tests, build and diff checks passed. PostgreSQL tests were not run locally; CI completion is deliberately not checked. Jira unchanged.
