"""KAN-48: end of selection (admitida / lista de espera / no admitida) with human decisions, enrollment, audit and scoped permissions."""

import itertools
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core import audit
from app.core.db import SessionLocal
from app.main import app
from app.modules.admissions.models import Application, ApplicationEvent
from app.modules.audit.models import AuditEvent
from app.modules.catalog.models import Call, Cohort
from app.modules.identity.models import Person, User
from app.modules.learning.models import Enrollment
from app.modules.selection.models import SelectionDecision
from tests.conftest import ADMIN, ASPIRANTE, CAPT_DATA, CAPT_IA, CODER, COORD, DOCENTE, SEL_IA, login

IA_CALL, DATA_CALL = "CONV-IA-2027A", "CONV-DATA-2027A"
IA_COHORT, DATA_COHORT = "COH-T-IA", "COH-T-DATA"
REASON = "Decisión tomada tras las entrevistas de selección"
counter = itertools.count(1)


@pytest.fixture(autouse=True)
def _single_signature_calls(db):
    """These tests cover the decision itself with quorum 1; the two-person quorum is tested in test_selection_quorum.py."""
    for call_id in (IA_CALL, DATA_CALL):
        db.get(Call, call_id).selection_quorum = 1
    db.commit()


def make_cohort(db, cohort_id=IA_COHORT, call_id=IA_CALL, program_id="P-IA") -> Cohort:
    cohort = Cohort(id=cohort_id, program_id=program_id, call_id=call_id, nombre="Cohorte sintética de prueba", inicio=date(2027, 3, 1), fin=date(2027, 9, 30))
    db.add(cohort)
    db.commit()
    return cohort


def make_application(db, call_id=IA_CALL, stage="pendiente_decision_humana") -> Application:
    n = next(counter)
    person = Person(display_name=f"Persona Sintética {n}", email=f"seleccion.{n}@example.test", is_synthetic=True)
    db.add(person)
    db.flush()
    prefix = db.scalar(select(Call.codigo_prefix).where(Call.id == call_id))
    application = Application(
        codigo=f"{prefix}-S{n:03d}", person_id=person.id, call_id=call_id, stage=stage,
        motivacion="Motivación sintética de prueba", disponibilidad="Flexible", acepta_datos_sinteticos=True,
    )
    db.add(application)
    db.commit()
    return application


def decide(client, who, application_id, decision="admitida", reason=REASON, cohort_id="default", **extra):
    body = {"decision": decision, "reason": reason, **extra}
    if cohort_id == "default":
        cohort_id = IA_COHORT if decision == "admitida" else None
    if cohort_id:
        body["cohort_id"] = cohort_id
    return client.post(f"/api/v1/applications/{application_id}/selection-decisions", json=body, headers=who)


def history(client, who, application_id):
    return client.get(f"/api/v1/applications/{application_id}/selection-decisions", headers=who)


def snapshot(db, application) -> tuple:
    """What a rejected request must leave untouched: stage, decisions, enrollments, CRM events and selection audit rows."""
    db.expire_all()
    return (
        db.get(Application, application.id).stage,
        db.scalar(select(func.count()).select_from(SelectionDecision)),
        db.scalar(select(func.count()).select_from(Enrollment)),
        db.scalar(select(func.count()).select_from(ApplicationEvent)),
        db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action.like("selection.%"))),
    )


def leave_one_place(db) -> None:
    """The seed already admits some applications of the call: leave exactly one free place on top of them."""
    admitted = db.scalar(select(func.count()).select_from(Application).where(Application.call_id == IA_CALL, Application.stage == "admitida"))
    db.get(Call, IA_CALL).plazas = admitted + 1
    db.commit()


def stage_of(db, application) -> str:
    db.expire_all()
    return db.get(Application, application.id).stage


def enrollments_of(db, application) -> list[Enrollment]:
    db.expire_all()
    return list(db.scalars(select(Enrollment).where(Enrollment.application_id == application.id)))


# ---------- the decision creates the enrollment, atomically ----------


def test_admission_enrols_the_person_and_records_who_when_and_why(client, db):
    make_cohort(db)
    target = make_application(db)
    response = decide(client, login(client, SEL_IA), target.id)
    assert response.status_code == 201, response.text
    body = response.json()
    assert (body["decision"], body["from_stage"], body["to_stage"], body["cohort_id"]) == ("admitida", "pendiente_decision_humana", "admitida", IA_COHORT)
    assert body["reason"] == REASON
    assert body["actor"] == db.scalar(select(User.display_name).where(User.email == SEL_IA))
    assert stage_of(db, target) == "admitida"
    (enrollment,) = enrollments_of(db, target)
    assert (enrollment.person_id, enrollment.cohort_id, enrollment.estado) == (target.person_id, IA_COHORT, "activa")
    assert body["enrollment_id"] == str(enrollment.id)


def test_crm_entry_has_fixed_text_and_audit_has_no_free_text(client, db):
    make_cohort(db)
    target = make_application(db)
    assert decide(client, login(client, SEL_IA), target.id, reason="Motivo reservado del equipo de selección").status_code == 201
    db.expire_all()
    event = db.scalars(select(ApplicationEvent).where(ApplicationEvent.application_id == target.id, ApplicationEvent.tipo == "cambio_etapa")).one()
    assert event.resumen == f"Selección terminada: admitida y matriculada en la cohorte {IA_COHORT}"
    assert event.actor_user_id is not None
    audit_row = db.scalars(select(AuditEvent).where(AuditEvent.action == "selection.decided")).one()
    assert audit_row.target_id == str(target.id)
    assert "reason" not in audit_row.meta and "Motivo reservado" not in str(audit_row.meta)
    assert audit_row.meta["decision"] == "admitida" and audit_row.meta["cohort_id"] == IA_COHORT


def test_waiting_list_does_not_enrol_and_can_be_promoted_later(client, db):
    make_cohort(db)
    target = make_application(db)
    who = login(client, SEL_IA)
    waiting = decide(client, who, target.id, "lista_espera")
    assert waiting.status_code == 201 and waiting.json()["enrollment_id"] is None and waiting.json()["cohort_id"] is None
    assert stage_of(db, target) == "lista_espera" and enrollments_of(db, target) == []
    before = snapshot(db, target)
    again = decide(client, who, target.id, "lista_espera")
    assert again.status_code == 409 and again.json()["code"] == "already_on_waiting_list"
    assert snapshot(db, target) == before
    promoted = decide(client, who, target.id)
    assert promoted.status_code == 201 and promoted.json()["from_stage"] == "lista_espera"
    assert stage_of(db, target) == "admitida" and len(enrollments_of(db, target)) == 1
    items = history(client, who, target.id).json()["items"]
    assert [i["decision"] for i in items] == ["lista_espera", "admitida"]


def test_not_admitted_enrols_nobody_and_closes_selection(client, db):
    make_cohort(db)
    target = make_application(db)
    who = login(client, COORD)
    assert decide(client, who, target.id, "no_admitida").status_code == 201
    assert stage_of(db, target) == "no_admitida" and enrollments_of(db, target) == []
    before = snapshot(db, target)
    closed = decide(client, who, target.id)
    assert closed.status_code == 409 and closed.json()["code"] == "selection_ended"
    assert snapshot(db, target) == before


def test_audit_failure_rolls_back_enrollment_stage_decision_and_crm(db, monkeypatch):
    make_cohort(db)
    target = make_application(db)
    before = snapshot(db, target)
    with TestClient(app, raise_server_exceptions=False) as client:
        actor = login(client, ADMIN)

        def fail_audit(*_args, **_kwargs):
            raise RuntimeError("Synthetic audit failure")

        with monkeypatch.context() as patch:
            patch.setattr(audit, "record", fail_audit)
            assert decide(client, actor, target.id).status_code == 500
    # Verify persisted rollback through a session independent of the failed request.
    with SessionLocal() as verification:
        assert snapshot(verification, target) == before


# ---------- permissions: selección and coordinación decide by default, inside their scope ----------

ALLOWED = [ADMIN, SEL_IA, COORD]


@pytest.mark.parametrize("who", ALLOWED)
def test_default_deciders_can_admit_inside_their_scope(client, db, who):
    make_cohort(db)
    target = make_application(db)
    assert decide(client, login(client, who), target.id).status_code == 201
    assert stage_of(db, target) == "admitida"


@pytest.mark.parametrize("who", [CAPT_IA, DOCENTE, ASPIRANTE, CODER])
def test_other_profiles_cannot_decide_or_read_admissions(client, db, who):
    make_cohort(db)
    target = make_application(db)
    before = snapshot(db, target)
    headers = login(client, who)
    assert decide(client, headers, target.id).status_code == 403
    assert history(client, headers, target.id).status_code == 403
    # A refused request leaves no trace, not even its own audit row.
    assert snapshot(db, target) == before


def test_anonymous_requests_are_unauthorised(client, db):
    make_cohort(db)
    target = make_application(db)
    assert decide(client, {}, target.id).status_code == 401
    assert history(client, {}, target.id).status_code == 401


def test_selection_only_decides_inside_its_own_call(client, db):
    make_cohort(db, DATA_COHORT, DATA_CALL, "P-DATA")
    other_call_application = make_application(db, DATA_CALL)
    before = snapshot(db, other_call_application)
    who = login(client, SEL_IA)
    assert decide(client, who, other_call_application.id, cohort_id=DATA_COHORT).status_code == 403
    assert history(client, who, other_call_application.id).status_code == 403
    assert snapshot(db, other_call_application) == before
    # Captación of another programme is refused too, before reading anything else.
    assert decide(client, login(client, CAPT_DATA), other_call_application.id, cohort_id=DATA_COHORT).status_code == 403


def test_history_is_readable_by_deciders_and_leaves_an_audit_trail(client, db):
    make_cohort(db)
    target = make_application(db)
    assert decide(client, login(client, SEL_IA), target.id).status_code == 201
    coord = login(client, COORD)
    items = history(client, coord, target.id).json()["items"]
    assert len(items) == 1 and items[0]["reason"] == REASON and items[0]["actor"]
    assert db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action == "selection.decisions_viewed")) == 1


def test_unknown_application_is_not_found(client):
    who = login(client, ADMIN)
    ghost = "00000000-0000-0000-0000-000000000000"
    assert decide(client, who, ghost).status_code == 404
    assert history(client, who, ghost).status_code == 404


# ---------- which applications can be decided ----------


@pytest.mark.parametrize("stage", ["enviada", "requisitos_en_revision"])
def test_cannot_decide_before_preselection_ends(client, db, stage):
    make_cohort(db)
    target = make_application(db, stage=stage)
    before = snapshot(db, target)
    response = decide(client, login(client, ADMIN), target.id)
    assert response.status_code == 409 and response.json()["code"] == "selection_not_started"
    assert snapshot(db, target) == before


@pytest.mark.parametrize("stage", ["convocada", "evaluacion_en_curso", "pendiente_decision_humana"])
def test_can_decide_from_any_selection_stage(client, db, stage):
    make_cohort(db)
    target = make_application(db, stage=stage)
    response = decide(client, login(client, ADMIN), target.id)
    assert response.status_code == 201 and response.json()["from_stage"] == stage


def test_withdrawn_application_cannot_be_decided(client, db):
    make_cohort(db)
    target = make_application(db, stage="retirada")
    before = snapshot(db, target)
    response = decide(client, login(client, ADMIN), target.id)
    assert response.status_code == 409 and response.json()["code"] == "application_withdrawn"
    assert snapshot(db, target) == before


def test_admitted_application_cannot_be_decided_again(client, db):
    make_cohort(db)
    target = make_application(db)
    admin = login(client, ADMIN)
    assert decide(client, admin, target.id).status_code == 201
    before = snapshot(db, target)
    for decision in ("admitida", "no_admitida", "lista_espera"):
        response = decide(client, admin, target.id, decision)
        assert response.status_code == 409 and response.json()["code"] == "selection_ended"
    assert snapshot(db, target) == before and len(enrollments_of(db, target)) == 1


# ---------- cohort, places and duplicates ----------


def test_cohort_must_belong_to_the_call_of_the_application(client, db):
    make_cohort(db)
    make_cohort(db, DATA_COHORT, DATA_CALL, "P-DATA")
    target = make_application(db)
    before = snapshot(db, target)
    admin = login(client, ADMIN)
    foreign = decide(client, admin, target.id, cohort_id=DATA_COHORT)
    missing = decide(client, admin, target.id, cohort_id="COH-NO-EXISTE")
    assert foreign.status_code == missing.status_code == 422
    # One answer for a cohort of another call and for one that does not exist: the response never confirms the former.
    assert foreign.json()["code"] == missing.json()["code"] == "cohort_not_in_call"
    assert foreign.json()["detail"] == missing.json()["detail"]
    assert snapshot(db, target) == before


def test_a_call_without_cohort_explains_what_to_do(client, db):
    target = make_application(db)
    response = decide(client, login(client, ADMIN), target.id, cohort_id=IA_COHORT)
    assert response.status_code == 422 and "administración" in response.json()["detail"]


def test_person_already_enrolled_in_the_cohort_is_not_enrolled_twice(client, db):
    make_cohort(db)
    target = make_application(db)
    db.add(Enrollment(person_id=target.person_id, cohort_id=IA_COHORT, estado="activa"))
    db.commit()
    before = snapshot(db, target)
    response = decide(client, login(client, ADMIN), target.id)
    assert response.status_code == 409 and response.json()["code"] == "already_enrolled"
    assert snapshot(db, target) == before


def test_admission_stops_when_the_places_of_the_call_are_taken(client, db):
    make_cohort(db)
    leave_one_place(db)
    first, second = make_application(db), make_application(db)
    admin = login(client, ADMIN)
    assert decide(client, admin, first.id).status_code == 201
    before = snapshot(db, second)
    full = decide(client, admin, second.id)
    assert full.status_code == 409 and full.json()["code"] == "no_places_left"
    assert "lista de espera" in full.json()["detail"]
    assert snapshot(db, second) == before
    # The suggested way out works: nobody is refused by the platform, and no place is consumed.
    assert decide(client, admin, second.id, "lista_espera").status_code == 201


def test_two_simultaneous_admissions_never_exceed_the_places(db):
    make_cohort(db)
    leave_one_place(db)
    first, second = make_application(db), make_application(db)
    with TestClient(app) as one, TestClient(app) as two:
        headers = [login(one, ADMIN), login(two, ADMIN)]
        gate = threading.Barrier(2)

        def attempt(client, who, target):
            gate.wait()
            return decide(client, who, target.id).status_code

        with ThreadPoolExecutor(2) as pool:
            codes = sorted(pool.map(attempt, [one, two], headers, [first, second]))
    assert codes == [201, 409]
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(Enrollment).where(Enrollment.cohort_id == IA_COHORT)) == 1


# ---------- input validation ----------


def test_admission_requires_a_cohort_and_other_decisions_forbid_it(client, db):
    make_cohort(db)
    target = make_application(db)
    before = snapshot(db, target)
    admin = login(client, ADMIN)
    assert decide(client, admin, target.id, cohort_id=None).status_code == 422
    assert decide(client, admin, target.id, "lista_espera", cohort_id=IA_COHORT).status_code == 422
    assert decide(client, admin, target.id, "no_admitida", cohort_id=IA_COHORT).status_code == 422
    assert snapshot(db, target) == before


@pytest.mark.parametrize("reason", ["", "   ", "x" * 501])
def test_reason_is_required_and_bounded(client, db, reason):
    make_cohort(db)
    target = make_application(db)
    before = snapshot(db, target)
    assert decide(client, login(client, ADMIN), target.id, reason=reason).status_code == 422
    assert snapshot(db, target) == before


def test_decision_cannot_force_a_stage_or_unknown_decisions(client, db):
    make_cohort(db)
    target = make_application(db)
    before = snapshot(db, target)
    admin = login(client, ADMIN)
    assert decide(client, admin, target.id, stage="admitida").status_code == 422
    assert decide(client, admin, target.id, "retirada_expresa", cohort_id=None).status_code == 422
    assert snapshot(db, target) == before


def test_database_refuses_an_admission_without_enrollment(db):
    make_cohort(db)
    target = make_application(db)
    actor = db.scalar(select(User.id).where(User.email == ADMIN))
    db.add(SelectionDecision(
        application_id=target.id, decision="admitida", from_stage="pendiente_decision_humana", to_stage="admitida",
        reason=REASON, actor_user_id=actor,
    ))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


# ---------- comparative view and waiting-list order (review of PR #95) ----------


def overview(client, who, call_id=IA_CALL):
    return client.get(f"/api/v1/calls/{call_id}/selection-overview", headers=who)


def empty_waiting_list(db, call_id=IA_CALL) -> None:
    """The seed may already have people on the waiting list: start the test with an empty one."""
    for application in db.scalars(select(Application).where(Application.call_id == call_id, Application.stage == "lista_espera")):
        application.stage = "no_admitida"
    db.commit()


def test_overview_puts_the_places_next_to_the_applications_in_selection(client, db):
    first = make_application(db, stage="convocada")
    second = make_application(db, stage="pendiente_decision_humana")
    response = overview(client, login(client, SEL_IA))
    assert response.status_code == 200, response.text
    body = response.json()
    call = db.get(Call, IA_CALL)
    admitted = db.scalar(select(func.count()).select_from(Application).where(Application.call_id == IA_CALL, Application.stage == "admitida"))
    assert (body["call_id"], body["plazas"], body["admitted"]) == (IA_CALL, call.plazas, admitted)
    assert body["free_places"] == max(call.plazas - admitted, 0)
    codes = {item["codigo"]: item["stage"] for item in body["candidates"]}
    assert codes[first.codigo] == "convocada" and codes[second.codigo] == "pendiente_decision_humana"
    assert body["in_selection"] == len(body["candidates"])
    assert all(item["stage"] in ("convocada", "evaluacion_en_curso", "pendiente_decision_humana") for item in body["candidates"])
    # The view shows codes and stages only: no names, emails or free text.
    assert set(body["candidates"][0]) == {"application_id", "codigo", "stage", "stage_label"}


def test_overview_never_reports_negative_free_places(client, db):
    admitted = db.scalar(select(func.count()).select_from(Application).where(Application.call_id == IA_CALL, Application.stage == "admitida"))
    db.get(Call, IA_CALL).plazas = max(admitted - 1, 0)
    db.commit()
    assert overview(client, login(client, COORD)).json()["free_places"] == 0


def test_waiting_list_is_ordered_by_entry_and_only_proposes_the_first(client, db):
    empty_waiting_list(db)
    applications = [make_application(db) for _ in range(3)]
    who = login(client, SEL_IA)
    for application in applications:
        assert decide(client, who, application.id, "lista_espera").status_code == 201
    body = overview(client, who).json()
    assert body["waiting"] == 3 and len(body["waiting_list"]) == 3
    assert [entry["codigo"] for entry in body["waiting_list"]] == [a.codigo for a in applications]
    assert [entry["position"] for entry in body["waiting_list"]] == [1, 2, 3]
    assert [entry["is_next"] for entry in body["waiting_list"]] == [True, False, False]
    assert body["waiting_order_basis"] == "entrada_en_lista" and body["waiting_order_confirmed"] is False


def test_promoting_from_the_waiting_list_moves_the_next_person_up(client, db):
    make_cohort(db)
    empty_waiting_list(db)
    leave_one_place(db)
    first, second = make_application(db), make_application(db)
    who = login(client, SEL_IA)
    for application in (first, second):
        assert decide(client, who, application.id, "lista_espera").status_code == 201
    assert decide(client, who, first.id).status_code == 201
    waiting = overview(client, who).json()["waiting_list"]
    assert [(entry["codigo"], entry["position"], entry["is_next"]) for entry in waiting] == [(second.codigo, 1, True)]


def test_promoting_out_of_order_is_allowed_but_audited(client, db):
    make_cohort(db)
    empty_waiting_list(db)
    leave_one_place(db)
    first, second = make_application(db), make_application(db)
    who = login(client, SEL_IA)
    for application in (first, second):
        assert decide(client, who, application.id, "lista_espera").status_code == 201
    assert decide(client, who, second.id).status_code == 201
    assert stage_of(db, second) == "admitida"
    db.expire_all()
    rows = db.scalars(select(AuditEvent).where(AuditEvent.action == "selection.decided").order_by(AuditEvent.id)).all()
    flags = [row.meta["out_of_waiting_order"] for row in rows]
    assert flags == [False, False, True]


def test_promoting_the_first_in_line_is_not_flagged(client, db):
    make_cohort(db)
    empty_waiting_list(db)
    leave_one_place(db)
    first, second = make_application(db), make_application(db)
    who = login(client, SEL_IA)
    for application in (first, second):
        assert decide(client, who, application.id, "lista_espera").status_code == 201
    assert decide(client, who, first.id).status_code == 201
    last = db.scalars(select(AuditEvent).where(AuditEvent.action == "selection.decided").order_by(AuditEvent.id.desc())).first()
    assert last.meta["out_of_waiting_order"] is False


@pytest.mark.parametrize("who", ALLOWED)
def test_overview_is_readable_by_deciders_and_leaves_an_audit_trail(client, db, who):
    assert overview(client, login(client, who)).status_code == 200
    assert db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action == "selection.overview_viewed")) == 1


@pytest.mark.parametrize("who", [CAPT_IA, DOCENTE, ASPIRANTE, CODER])
def test_other_profiles_cannot_read_the_overview(client, db, who):
    assert overview(client, login(client, who)).status_code == 403
    assert db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action == "selection.overview_viewed")) == 0


def test_overview_respects_the_scope_of_the_call(client, db):
    assert overview(client, login(client, SEL_IA), DATA_CALL).status_code == 403
    assert overview(client, login(client, ADMIN), DATA_CALL).status_code == 200


def test_overview_of_an_unknown_call_is_not_found_and_anonymous_is_refused(client):
    assert overview(client, login(client, ADMIN), "CONV-NO-EXISTE").status_code == 404
    assert client.get(f"/api/v1/calls/{IA_CALL}/selection-overview").status_code == 401
