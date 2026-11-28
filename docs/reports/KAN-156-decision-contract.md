# KAN-156 · Contrato de decisión y lista de espera / Decision and waiting-list contract

Fecha / Date: 2026-11-27. Código revisado / Code reviewed: `dev@746f386` (`api/app/modules/selection/`, `contracts/openapi.json`). Datos sintéticos / Synthetic data only.

**ES** — El título habla de `AdmissionDecision` y `WaitlistEntry`. En el código son `SelectionDecision` y `WaitingListEntry`.

**EN** — The title says `AdmissionDecision` and `WaitlistEntry`. The code names them `SelectionDecision` and `WaitingListEntry`.

## Contrato / Contract (`/api/v1`)

| Operación / Operation | Respuestas documentadas / Documented responses |
|---|---|
| `POST /applications/{id}/selection-decisions` | 201, 202, 403, 404, 409, 422 |
| `GET /applications/{id}/selection-decisions` | 200, 403, 404, 422 |
| `GET /calls/{id}/selection-overview` | 200, 403, 404, 422 |
| `GET`, `PUT /calls/{id}/selection-policy` | 200, 403, 404, 422 |

- **201** — ES: decisión aplicada (`SelectionDecisionOut`, con sus votos). EN: decision applied, with its votes.
- **202** — ES: voto guardado, falta acuerdo (`SelectionPendingOut`; `state` es `pending` o `disagreement`). EN: vote stored, agreement still missing.
- **GET** — `SelectionDecisionList`: `items`, `quorum`, `pending_votes`.
- **Decisiones / Decisions** — `admitida`, `lista_espera`, `no_admitida`. Entrada / Input: `decision`, `reason`, `cohort_id`.

## Lista de espera / Waiting list

**ES** — `WaitingListEntry` (`application_id`, `codigo`, `position`, `since`, `is_next`) **se calcula** en `selection-overview`; no hay una tabla propia. Las tablas del módulo son `selection_decision`, `selection_approval` y `selection_appointment`. El orden es por entrada en la lista, y la API lo marca como no confirmado (`waiting_order_confirmed`). Nadie se promueve solo.

**EN** — `WaitingListEntry` is **computed** in `selection-overview`; it has no table of its own. Order is by entry into the list, flagged by the API as unconfirmed (`waiting_order_confirmed`). Nobody is promoted automatically.

## Validaciones / Validations

Ámbito de convocatoria, etapa de la candidatura, cohorte de la convocatoria, persona no matriculada ya en la cohorte, cupo, sin comprobación de identidad pendiente para admitir (409 `dossier_check_pending`), un voto abierto por persona y motivo obligatorio y acotado. Una admisión crea la matrícula en la misma transacción. / Call scope, application stage, cohort belongs to the call, person not already enrolled, capacity, no pending identity check when admitting (409 `dossier_check_pending`), one open vote per person, mandatory bounded reason. An admission creates the enrollment in the same transaction.

## Evidencia / Evidence

PostgreSQL 16.15 con pgvector, desechable y local; Python 3.13.15 (CI: 3.12). Sobre / On `dev@746f386`, **370 passed**: los archivos de prueba que mencionan un endpoint o modelo de selección, más solicitudes, matriz de permisos y contrato / every test file mentioning a selection endpoint or model, plus applications, RBAC matrix and contract. Incluye una prueba de KAN-175 aún en su propia rama / Includes a KAN-175 test still on its own branch. Principales / Main: `test_selection_decisions.py`, `test_selection_quorum.py`, `test_selection_vote_evidence.py`, `test_contract.py`.

No ejecutado / Not run: comprobación de que `src/shared/api/schema.gen.ts` está regenerado / freshness check of the generated TypeScript client.

## Pendiente de aceptación de PO / Awaiting PO acceptance

**ES**

1. ¿Vale una lista de espera calculada, o `WaitlistEntry` debe persistirse?
2. La política del 22/11 (KAN-147) dice que la plaza se ocupa al admitir y que la matrícula posterior no la consume otra vez. Hoy admisión y matrícula ocurren a la vez. ¿Es aceptable?
3. Criterio definitivo de orden de la lista de espera.
4. La liberación de plaza por renuncia o baja no está en `dev` (KAN-164).
5. Revisión cruzada de David.

**EN**

1. Is a computed waiting list acceptable, or must `WaitlistEntry` be persisted?
2. The 22/11 policy (KAN-147) says the place is taken at admission and a later enrollment does not take it again. Today admission and enrollment happen together. Is that acceptable?
3. Final ordering rule for the waiting list.
4. Releasing a place after resignation or withdrawal is not on `dev` (KAN-164).
5. Cross-review by David.

> **ES** — `746f386` tenía una sola cabecera Alembic (`0024_merge_heads`). El `dev` posterior (`933e0e9`) tiene dos; las corrige PR #296.
> **EN** — `746f386` had a single Alembic head (`0024_merge_heads`). The later `dev` (`933e0e9`) has two; PR #296 fixes them.
