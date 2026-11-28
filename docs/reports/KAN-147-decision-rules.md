# KAN-147 · Autoridad de decisión y reglas de cupos / Decision authority and capacity rules

Fecha / Date: 2026-11-27. Código revisado / Code reviewed: `dev@746f386`.

**ES** — Este documento recoge reglas ya registradas en Jira y las contrasta con el código. No crea reglas nuevas.

**EN** — This document records rules already written in Jira and compares them with the code. It creates no new rule.

## Fuentes / Sources

- KAN-147, comentario PO del 18/11 / PO comment of 18/11: la lista de espera es una referencia; una excepción exige criterios humanos definidos por convocatoria, justificación y traza; no hay adjudicación automática. / The waiting list is a reference; an exception needs human criteria defined per call, a justification and a trace; nothing is allocated automatically.
- [KAN-147, política aprobada por PO el 22/11 / policy approved by the PO on 22/11](https://anasfady87-1789923749606.atlassian.net/browse/KAN-147?focusedCommentId=10225).
- [KAN-147, reconciliación del 23/11 / reconciliation of 23/11](https://anasfady87-1789923749606.atlassian.net/browse/KAN-147?focusedCommentId=10284): recoge que Melissa confirmó un quórum mínimo por defecto de dos personas. / The 23/11 reconciliation records that Melissa confirmed a default quorum of two people.

## Regla aprobada frente a código / Approved rule vs. code

| Regla (22/11) / Rule | Estado en `dev` / State on `dev` |
|---|---|
| Decisión humana y conjunta / Human joint decision | **Parcial / Partial**: decisión humana conjunta por defecto mediante `selection_approval`; con quórum 1 se aplica una decisión final con una sola firma (`test_quorum_one_keeps_the_single_signature_behaviour`). La excepción de un firmante requiere confirmación explícita de PO; no consta aprobada en la política del 22/11. / Joint human decision by default through `selection_approval`; quorum 1 applies a final decision with a single signature (same regression test). The single-signer exception requires explicit PO confirmation; it is not explicitly approved by the 22/11 policy. |
| Quórum por defecto 2, configurable por convocatoria / Default quorum 2, configurable per call | **Configuración implementada / Configuration implemented**: 1–5; solo administración, auditado. La aceptación del valor 1 sigue pendiente (véase fila anterior). / Administration only, audited; acceptance of value 1 remains pending (see previous row). |
| Una persona no puede dar dos aprobaciones / One person cannot give two approvals | **Implementado / Done** |
| Cada decisión queda auditada / Every decision is audited | **Implementado / Done** |
| Roles autorizados configurables por convocatoria / Authorised roles configurable per call | **No implementado / Not done**: `selection.decide` está fijo por rol en / is fixed per role in `api/app/core/authz.py` |
| La plaza se ocupa con la admisión definitiva y no se consume otra vez / Place taken at definitive admission, never twice | **Parcial / Partial**: `_check_places` cuenta candidaturas en etapa `admitida`, por convocatoria, sin contar matrículas por separado. Sin embargo, `_apply` crea `Enrollment` en la misma transacción que la admisión. El paso independiente de matrícula posterior que no consume otra plaza, exigido por la política del 22/11, no está implementado en la versión revisada; reconciliar con KAN-156 y KAN-164. / `_check_places` counts admitted applications per call, not enrollments separately. However, `_apply` creates `Enrollment` in the same transaction as admission. The separate later enrollment step without additional capacity consumption required by the 22/11 policy is not implemented in the reviewed version; reconcile with KAN-156 and KAN-164. |
| Cupo por cohorte / Capacity scoped to the cohort | **No implementado / Not done**: el cupo es `call.plazas`, por convocatoria / capacity is per call. La cohorte sí es obligatoria para admitir / A cohort is mandatory to admit |
| Orden de espera orientativo; excepción justificada y auditada; sin superar el cupo / Advisory order; justified and audited exception; never over capacity | **Parcial / Partial**: el motivo es obligatorio y la auditoría marca `out_of_waiting_order`; no hay justificación específica de la excepción / the reason is mandatory and the audit flags it; there is no exception-specific justification |
| Criterios de excepción definidos por convocatoria (18/11) / Exception criteria defined per call | **No implementado / Not done** |
| Sin asignación automática / No automatic allocation | **Implementado / Done** |

Pruebas / Tests: `api/tests/test_selection_quorum.py` y/and `test_selection_decisions.py`; incluidas en las 370 pruebas que pasaron el 27/11 en PostgreSQL 16.15 desechable / part of the 370 tests that passed on 27/11 on a disposable PostgreSQL 16.15.

## Pendiente / Pending

**ES**

1. Liberar la plaza tras una renuncia o baja: no está en `dev`; es trabajo de KAN-164.
2. Decidir si el cupo por cohorte y los roles por convocatoria entran antes de la congelación, o quedan como alcance diferido. Hace falta decisión de PO.
3. Ingreso fuera de plazo: en Jira figura pendiente de Melissa (reconciliación del 23/11). El código de KAN-164, sin publicar, menciona una decisión de PO del 26/11 que la fundación no ha confirmado.
4. Confirmar explícitamente si se admite quórum 1 como excepción a la decisión conjunta; reconciliar la matrícula posterior independiente con KAN-156/KAN-164.
5. Revisión cruzada de Yohanna.

**EN**

1. Releasing a place after resignation or withdrawal is not on `dev`; it belongs to KAN-164.
2. Decide whether cohort capacity and per-call roles go in before the freeze or become deferred scope. A PO decision is needed.
3. Late intake: Jira lists it as pending from Melissa (23/11 reconciliation). The unpublished KAN-164 code mentions a PO decision of 26/11 that the foundation has not confirmed.
4. Explicitly confirm whether quorum 1 is accepted as an exception to joint decision-making; reconcile separate later enrollment with KAN-156/KAN-164.
5. Cross-review by Yohanna.

> **ES** — `746f386` tenía una sola cabecera Alembic (`0024_merge_heads`). El `dev` posterior (`933e0e9`) tiene dos; las corrige PR #296.
> **EN** — `746f386` had a single Alembic head (`0024_merge_heads`). The later `dev` (`933e0e9`) has two; PR #296 fixes them.
