# KAN-163 · Evidencia en PostgreSQL / PostgreSQL evidence

Fecha / Date: 2026-11-27. Código probado / Code under test: `dev@746f386`. Datos sintéticos / Synthetic data only.

## ES — Resumen

El 24/11 quedó registrado en Jira que los dos escenarios de PR #147 se habían recopilado, pero no ejecutado en PostgreSQL. Hoy se ejecutaron y pasan. El ticket **no queda completo**: faltan los escenarios de renuncia y baja.

## EN — Summary

On 24/11 Jira recorded that the two PR #147 scenarios had been collected but not run on PostgreSQL. They were run today and pass. The ticket is **not complete**: the resignation and withdrawal scenarios are missing.

## Cubierto / Covered

Archivos en / Files in `api/tests/`.

| Escenario / Scenario | Prueba / Test |
|---|---|
| Fallo en la firma final: rollback y reintento / Failed final signature: rollback and retry | `test_final_quorum_transaction.py::test_failed_final_signature_rolls_back_only_its_transaction_and_retry_can_succeed` |
| La última plaza se ocupa entre dos firmas / Last place taken between two signatures | `test_final_quorum_transaction.py::test_another_admission_can_consume_the_last_place_between_two_signatures` |
| Dos candidaturas en espera compiten por la última plaza / Two waitlisted applications contend for the last place | `test_waitlist_last_place.py::test_two_waitlisted_applications_contend_for_the_last_seat_at_final_signature` |
| Sin plazas / No places left | `test_selection_decisions.py::test_admission_stops_when_the_places_of_the_call_are_taken` |
| Admisiones simultáneas sin superar el cupo / Concurrent admissions never exceed the places | `test_selection_decisions.py::test_two_simultaneous_admissions_never_exceed_the_places` |
| Fallo de auditoría / Audit failure | `test_selection_decisions.py::test_audit_failure_rolls_back_enrollment_stage_decision_and_crm` |
| Voto repetido de la misma persona / Same person voting twice | `test_selection_quorum.py::test_the_same_person_cannot_vote_twice` |
| Votos simultáneos: una sola decisión y matrícula / Concurrent votes: one decision and enrollment | `test_selection_quorum.py::test_two_simultaneous_agreeing_votes_create_exactly_one_decision_and_enrollment`, `::test_three_simultaneous_votes_with_quorum_two_still_decide_once` |
| Excepción al orden de espera, auditada / Out-of-order promotion, audited | `test_selection_decisions.py::test_promoting_out_of_order_is_allowed_but_audited` |

## Ejecución / Run

PostgreSQL 16.15 con pgvector, desechable y local / disposable and local. Python 3.13.15 (CI: 3.12). Desde / From `api/`:

- `pytest` sobre los archivos de prueba que mencionan un endpoint o modelo de selección, más `test_applications.py`, `test_rbac_matrix.py` y `test_contract.py` / on every test file mentioning a selection endpoint or model, plus those three: **370 passed**. Incluye una prueba nueva de KAN-175, aún en su propia rama / This includes a new KAN-175 test that is still on its own branch.
- `pytest tests/test_final_quorum_transaction.py tests/test_waitlist_last_place.py -v`: **3 passed**.

## Pendiente / Pending

**ES** — La retirada antes de la admisión (`retirada_expresa`) sí existe y tiene pruebas en `test_preselection_closure.py`. Hoy admisión y matrícula ocurren a la vez.

**EN** — Withdrawal before admission (`retirada_expresa`) does exist and is tested in `test_preselection_closure.py`. Today admission and enrollment happen together.

**ES** — Escenarios de aceptación del 22/11 que `dev@746f386` no cubre: renuncia o baja de una persona ya admitida, liberación de exactamente una plaza, repetición idempotente, admitir tras liberar, rechazo de una baja no autorizada, historial tras la baja y ventana de admisión fuera de plazo. La liberación de plaza no existe todavía en `dev`; se trabaja en KAN-164, sin publicar a esta fecha.

**EN** — Acceptance scenarios from 22/11 not covered by `dev@746f386`: resignation or withdrawal of an already admitted person, release of exactly one place, idempotent repetition, admission after a release, rejection of an unauthorised withdrawal, history after withdrawal, and the late-intake window. Releasing a place does not exist on `dev` yet; it is being built under KAN-164, unpublished at this date.

> **ES** — `746f386` tenía una sola cabecera Alembic (`0024_merge_heads`). El `dev` posterior (`933e0e9`) tiene dos; las corrige PR #296.
> **EN** — `746f386` had a single Alembic head (`0024_merge_heads`). The later `dev` (`933e0e9`) has two; PR #296 fixes them.
