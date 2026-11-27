# KAN-147 · Autoridad de decisión y reglas de cupos / Decision authority and capacity rules

Fecha / Date: 2026-11-27. Código revisado / Code reviewed: `dev@746f386`.

**ES** — Este documento recoge reglas ya registradas en Jira y las contrasta con el código. No crea reglas nuevas.

**EN** — This document records rules already written in Jira and compares them with the code. It creates no new rule.

## Fuentes / Sources

- KAN-147, comentario PO del 18/11 / PO comment of 18/11: la lista de espera es una referencia; una excepción exige criterios humanos definidos por convocatoria, justificación y traza; no hay adjudicación automática. / The waiting list is a reference; an exception needs human criteria defined per call, a justification and a trace; nothing is allocated automatically.
- KAN-147, política aprobada por PO el 22/11 / policy approved by the PO on 22/11.
- KAN-147, reconciliación del 23/11: recoge que Melissa confirmó un quórum mínimo por defecto de dos personas. / The 23/11 reconciliation records that Melissa confirmed a default quorum of two people.

## Regla aprobada frente a código / Approved rule vs. code

| Regla (22/11) / Rule | Estado en `dev` / State on `dev` |
|---|---|
| Decisión humana y conjunta / Human joint decision | **Implementado / Done** (`selection_approval`) |
| Quórum por defecto 2, configurable por convocatoria / Default quorum 2, configurable per call | **Implementado / Done**: 1–5; solo administración, auditado / administration only, audited |
| Una persona no puede dar dos aprobaciones / One person cannot give two approvals | **Implementado / Done** |
| Cada decisión queda auditada / Every decision is audited | **Implementado / Done** |
| Roles autorizados configurables por convocatoria / Authorised roles configurable per call | **No implementado / Not done**: `selection.decide` está fijo por rol en / is fixed per role in `api/app/core/authz.py` |
| La plaza se ocupa con la admisión definitiva y no se consume otra vez / Place taken at definitive admission, never twice | **Implementado / Done**: se cuentan candidaturas en etapa `admitida` / applications in stage `admitida` are counted |
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
4. Revisión cruzada de Yohanna.

**EN**

1. Releasing a place after resignation or withdrawal is not on `dev`; it belongs to KAN-164.
2. Decide whether cohort capacity and per-call roles go in before the freeze or become deferred scope. A PO decision is needed.
3. Late intake: Jira lists it as pending from Melissa (23/11 reconciliation). The unpublished KAN-164 code mentions a PO decision of 26/11 that the foundation has not confirmed.
4. Cross-review by Yohanna.

> **ES** — `746f386` tenía una sola cabecera Alembic (`0024_merge_heads`). El `dev` posterior (`933e0e9`) tiene dos; las corrige PR #296.
> **EN** — `746f386` had a single Alembic head (`0024_merge_heads`). The later `dev` (`933e0e9`) has two; PR #296 fixes them.
