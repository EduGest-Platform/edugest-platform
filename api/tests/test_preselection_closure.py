"""KAN-153: end of pre-selection (convocada / retirada expresa / silencio) with human decisions, audit and scoped permissions."""

import itertools
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select
from sqlalchemy.exc import IntegrityError

from app.core import audit
from app.core.db import SessionLocal, engine, utcnow
from app.main import app
from app.modules.admissions.models import Application, ApplicationEvent
from app.modules.audit.models import AuditEvent
from app.modules.catalog.models import Call
from app.modules.identity.models import Person, User
from app.modules.preselection.models import PreselectionDecision
from app.modules.requirements.models import CallRequirement, RequirementReview
from tests.conftest import ADMIN, API_DIR, ASPIRANTE, CAPT_DATA, CAPT_IA, CODER, COORD, DOCENTE, SEL_IA, login

IA_CALL, DATA_CALL, IA_CLOSED_CALL = "CONV-IA-2027A", "CONV-DATA-2027A", "CONV-IA-2026B"
REASON = "Decisión tomada tras revisar el expediente"
counter = itertools.count(1)


def make_application(db, call_id=IA_CALL, stage="requisitos_en_revision") -> Application:
    n = next(counter)
    person = Person(display_name=f"Persona Sintética {n}", email=f"preseleccion.{n}@example.test", is_synthetic=True)
    db.add(person)
    db.flush()
    prefix = db.scalar(select(Call.codigo_prefix).where(Call.id == call_id))
    application = Application(
        codigo=f"{prefix}-T{n:03d}", person_id=person.id, call_id=call_id, stage=stage,
        motivacion="Motivación sintética de prueba", disponibilidad="Flexible", acepta_datos_sinteticos=True,
    )
    db.add(application)
    db.commit()
    return application


def add_contacts(db, application, *attempts) -> None:
    """attempts: (days ago, result) pairs recorded as contact events."""
    for days_ago, result in attempts:
        db.add(ApplicationEvent(application_id=application.id, tipo="contacto", canal="telefono", resultado=result, resumen="Contacto sintético", occurred_at=utcnow() - timedelta(days=days_ago)))
    db.commit()


def configure_requirements(db, call_id, *refs) -> None:
    """KAN-135: a review needs a configured call requirement. Test-only catalogue, never in the product seed."""
    author_id = db.scalar(select(User.id).where(User.email == ADMIN))
    for ref in refs:
        db.add(CallRequirement(call_id=call_id, ref=ref, code=ref, version=1, label="Synthetic test requirement", kind="required", created_by=author_id))
    db.commit()


def silent_for(db, application, attempts=4, days=31) -> None:
    add_contacts(db, application, *[(days + (attempts - 1 - i) * 3, "sin_respuesta") for i in range(attempts)])


def decide(client, who, application_id, decision="convocada", reason=REASON, **extra):
    return client.post(f"/api/v1/applications/{application_id}/preselection-decisions", json={"decision": decision, "reason": reason, **extra}, headers=who)


def history(client, who, application_id):
    return client.get(f"/api/v1/applications/{application_id}/preselection-decisions", headers=who)


def snapshot(db, application) -> tuple:
    """What a rejected request must leave untouched: stage, decisions, CRM events and preselection audit rows."""
    db.expire_all()
    return (
        db.get(Application, application.id).stage,
        db.scalar(select(func.count()).select_from(PreselectionDecision)),
        db.scalar(select(func.count()).select_from(ApplicationEvent)),
        db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action.like("preselection.%"))),
    )


def stage_of(db, application) -> str:
    db.expire_all()
    return db.get(Application, application.id).stage


def test_audit_failure_rolls_back_stage_decision_and_crm(db, monkeypatch):
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


# ---------- permissions: five internal profiles, each inside its own scope ----------

ALLOWED = [(ADMIN, IA_CALL), (CAPT_IA, IA_CALL), (SEL_IA, IA_CALL), (COORD, IA_CALL), (DOCENTE, IA_CLOSED_CALL)]


@pytest.mark.parametrize(("who", "call_id"), ALLOWED)
def test_each_internal_profile_can_end_preselection_inside_its_scope(client, db, who, call_id):
    target = make_application(db, call_id)
    response = decide(client, login(client, who), target.id)
    assert response.status_code == 201, response.text
    body = response.json()
    assert (body["from_stage"], body["to_stage"], body["decision"]) == ("requisitos_en_revision", "convocada", "convocada")
    assert body["actor"] == db.scalar(select(User.display_name).where(User.email == who))
    assert stage_of(db, target) == "convocada"


DENIED = [
    (CAPT_DATA, IA_CALL), (SEL_IA, DATA_CALL), (CAPT_IA, DATA_CALL),
    (DOCENTE, IA_CALL),  # the open call feeds no cohort, so the teacher's cohort scope does not reach it
    (ASPIRANTE, IA_CALL), (CODER, IA_CALL),
]


@pytest.mark.parametrize(("who", "call_id"), DENIED)
@pytest.mark.parametrize("decision", ["convocada", "retirada_expresa", "silencio_confirmado", "silencio_reprogramado"])
def test_out_of_scope_and_person_accounts_get_403_without_any_change(client, db, who, call_id, decision):
    target = make_application(db, call_id)
    silent_for(db, target)
    before = snapshot(db, target)
    assert decide(client, login(client, who), target.id, decision).status_code == 403
    assert snapshot(db, target) == before


def test_anonymous_and_unknown_application_are_rejected(client, db):
    target = make_application(db)
    before = snapshot(db, target)
    assert decide(client, {}, target.id).status_code == 401
    assert decide(client, login(client, ADMIN), "00000000-0000-0000-0000-000000000000").status_code == 404
    assert snapshot(db, target) == before


@pytest.mark.parametrize("who", [CAPT_DATA, ASPIRANTE, CODER])
def test_reading_history_policy_and_alerts_is_scoped_too(client, db, who):
    target = make_application(db)
    headers = login(client, who)
    assert history(client, headers, target.id).status_code == 403
    assert client.get(f"/api/v1/calls/{IA_CALL}/preselection-policy", headers=headers).status_code == 403
    assert client.get(f"/api/v1/calls/{IA_CALL}/silence-review", headers=headers).status_code == 403


def test_decisions_are_not_exposed_to_the_person_or_to_the_public_catalogue(client, db):
    target = make_application(db)
    assert decide(client, login(client, ADMIN), target.id, "retirada_expresa", reason="Motivo interno confidencial").status_code == 201
    person_view = client.get("/api/v1/me/applications", headers=login(client, ASPIRANTE))
    assert "Motivo interno confidencial" not in person_view.text and "preselection" not in person_view.text
    calls = client.get("/api/v1/calls")
    assert "silence" not in calls.text


# ---------- convocatoria: ends pre-selection even with open requirements ----------


@pytest.mark.parametrize("stage", ["enviada", "requisitos_en_revision"])
def test_call_to_selection_ends_preselection_from_both_open_stages(client, db, stage):
    target = make_application(db, stage=stage)
    assert decide(client, login(client, SEL_IA), target.id).status_code == 201
    assert stage_of(db, target) == "convocada"


def test_open_requirements_do_not_block_the_call_and_are_recorded_as_evidence(client, db):
    target = make_application(db)
    configure_requirements(db, IA_CALL, "identity-document", "residence")
    admin = login(client, ADMIN)
    assert client.put(f"/api/v1/applications/{target.id}/requirement-reviews/identity-document", json={"result": "not_met", "reason": "Falta el documento"}, headers=admin).status_code == 201
    assert client.put(f"/api/v1/applications/{target.id}/requirement-reviews/residence", json={"result": "met", "reason": "Comprobado"}, headers=admin).status_code == 201
    response = decide(client, admin, target.id)
    assert response.status_code == 201
    assert response.json()["evidence"] == {"unresolved_requirement_reviews": 1}
    assert db.scalar(select(func.count()).select_from(RequirementReview).where(RequirementReview.application_id == target.id)) == 2


@pytest.mark.parametrize("stage", ["convocada", "evaluacion_en_curso", "pendiente_decision_humana", "admitida", "lista_espera", "no_admitida", "retirada"])
def test_only_applications_still_in_preselection_can_be_called_to_selection(client, db, stage):
    target = make_application(db, stage=stage)
    before = snapshot(db, target)
    response = decide(client, login(client, ADMIN), target.id, "convocada")
    assert response.status_code == 409
    assert response.json()["code"] == "preselection_ended"
    assert snapshot(db, target) == before


@pytest.mark.parametrize("stage", ["convocada", "evaluacion_en_curso", "pendiente_decision_humana"])
def test_a_person_can_also_withdraw_during_selection(client, db, stage):
    """PO decision 19/11/2026: withdrawal is always available during pre-selection and selection."""
    target = make_application(db, stage=stage)
    response = decide(client, login(client, SEL_IA), target.id, "retirada_expresa", reason="La persona comunica que no continúa")
    assert response.status_code == 201, response.text
    assert (response.json()["from_stage"], response.json()["to_stage"]) == (stage, "retirada")
    assert stage_of(db, target) == "retirada"


def test_withdrawal_after_admission_points_to_the_enrollment_withdrawal(client, db):
    target = make_application(db, stage="admitida")
    before = snapshot(db, target)
    response = decide(client, login(client, ADMIN), target.id, "retirada_expresa")
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "withdrawal_after_admission" and "matrícula" in body["detail"]
    assert snapshot(db, target) == before


@pytest.mark.parametrize("stage", ["lista_espera", "no_admitida", "retirada"])
def test_withdrawal_is_not_recorded_once_the_process_has_ended(client, db, stage):
    target = make_application(db, stage=stage)
    before = snapshot(db, target)
    response = decide(client, login(client, ADMIN), target.id, "retirada_expresa")
    assert response.status_code == 409 and response.json()["code"] == "withdrawal_not_available"
    assert snapshot(db, target) == before


@pytest.mark.parametrize("stage", ["convocada", "evaluacion_en_curso", "pendiente_decision_humana"])
@pytest.mark.parametrize("decision", ["silencio_confirmado", "silencio_reprogramado"])
def test_silence_decisions_only_apply_during_preselection(client, db, stage, decision):
    target = make_application(db, stage=stage)
    silent_for(db, target)
    response = decide(client, login(client, ADMIN), target.id, decision)
    assert response.status_code == 409 and response.json()["code"] == "preselection_ended"


def test_error_messages_are_written_for_non_technical_people(client, db):
    """PO decision 19/11/2026: the UI shows a plain message and a stable code, never just «409»."""
    target = make_application(db)
    add_contacts(db, target, (40, "sin_respuesta"), (35, "sin_respuesta"))
    body = decide(client, login(client, ADMIN), target.id, "silencio_confirmado").json()
    assert body["code"] == "silence_threshold_not_met"
    assert "2 intentos sin respuesta" in body["detail"] and "retirada expresa" in body["detail"]
    assert "409" not in body["detail"] and "threshold" not in body["detail"]
    denied = decide(client, login(client, CAPT_DATA), target.id).json()
    assert denied["code"] == "no_scope_permission" and "administración" in denied["detail"]


def test_a_second_decision_on_the_same_application_is_a_conflict(client, db):
    target = make_application(db)
    admin = login(client, ADMIN)
    assert decide(client, admin, target.id).status_code == 201
    before = snapshot(db, target)
    assert decide(client, admin, target.id, "silencio_confirmado").status_code == 409
    assert snapshot(db, target) == before


def test_two_simultaneous_decisions_produce_exactly_one_decision(db):
    target = make_application(db)
    with TestClient(app) as first, TestClient(app) as second:
        headers = [login(first, ADMIN), login(second, ADMIN)]
        gate = threading.Barrier(2)

        def attempt(client, who):
            gate.wait()
            return decide(client, who, target.id).status_code

        with ThreadPoolExecutor(2) as pool:
            codes = sorted(pool.map(attempt, [first, second], headers))
    assert codes == [201, 409]
    assert snapshot(db, target)[1] == 1


# ---------- retirada expresa ----------


def test_express_withdrawal_ends_preselection_and_keeps_who_when_and_why(client, db):
    target = make_application(db, stage="enviada")
    response = decide(client, login(client, CAPT_IA), target.id, "retirada_expresa", reason="La persona avisó por correo que desiste")
    assert response.status_code == 201
    assert stage_of(db, target) == "retirada"
    with TestClient(app) as other_session:
        items = history(other_session, login(other_session, SEL_IA), target.id).json()["items"]
    assert [(i["decision"], i["from_stage"], i["to_stage"], i["reason"]) for i in items] == [("retirada_expresa", "enviada", "retirada", "La persona avisó por correo que desiste")]
    assert items[0]["actor"] and items[0]["occurred_at"]


# ---------- input validation ----------


@pytest.mark.parametrize(
    "payload",
    [
        {"decision": "convocada", "reason": ""}, {"decision": "convocada", "reason": "   "}, {"decision": "convocada", "reason": "x" * 501},
        {"decision": "convocada"}, {"reason": REASON}, {"decision": "admitida", "reason": REASON}, {"decision": "descartada", "reason": REASON},
        {"decision": "convocada", "reason": REASON, "actor": "forged"}, {"decision": "convocada", "reason": REASON, "to_stage": "admitida"},
    ],
)
def test_invalid_payloads_are_rejected_without_changes(client, db, payload):
    target = make_application(db)
    before = snapshot(db, target)
    response = client.post(f"/api/v1/applications/{target.id}/preselection-decisions", json=payload, headers=login(client, ADMIN))
    assert response.status_code == 422
    assert snapshot(db, target) == before


# ---------- silence: a proposal for human review, never an automatic closure ----------

NO_ALERT = {
    "no contact attempts": [],
    "a single unanswered attempt": [(60, "sin_respuesta")],
    "attempts without a recorded result": [(90, None), (80, None), (70, None), (60, None)],
    "the person answered after the unanswered attempts": [(90, "sin_respuesta"), (80, "sin_respuesta"), (70, "sin_respuesta"), (60, "sin_respuesta"), (45, "respondida")],
}
# Light alert (PO 19/11/2026): from 2 unanswered attempts, with no waiting days, but below the action threshold.
LIGHT_ALERT = {
    "two attempts the same day": [(0, "sin_respuesta"), (0, "sin_respuesta")],
    "fewer attempts than the action threshold": [(60, "sin_respuesta"), (50, "sin_respuesta"), (40, "sin_respuesta")],
    "recent last attempt": [(70, "sin_respuesta"), (50, "sin_respuesta"), (30, "sin_respuesta"), (10, "sin_respuesta")],
}
NOT_YET_SILENCE = {**NO_ALERT, **LIGHT_ALERT}


@pytest.mark.parametrize("case", list(NO_ALERT))
def test_without_an_alert_silence_cannot_be_confirmed_or_postponed(client, db, case):
    target = make_application(db)
    add_contacts(db, target, *NO_ALERT[case])
    admin = login(client, ADMIN)
    before = snapshot(db, target)
    assert decide(client, admin, target.id, "silencio_confirmado").status_code == 409
    assert decide(client, admin, target.id, "silencio_reprogramado").json()["code"] == "no_silence_alert"
    assert snapshot(db, target) == before
    assert client.get(f"/api/v1/calls/{IA_CALL}/silence-review", headers=admin).json()["items"] == []


@pytest.mark.parametrize("case", list(LIGHT_ALERT))
def test_light_alert_is_listed_but_silence_cannot_be_confirmed_yet(client, db, case):
    target = make_application(db)
    add_contacts(db, target, *LIGHT_ALERT[case])
    admin = login(client, ADMIN)
    [item] = client.get(f"/api/v1/calls/{IA_CALL}/silence-review", headers=admin).json()["items"]
    assert item["evidence"]["alert_level"] == "leve" and item["evidence"]["threshold_met"] is False
    before = snapshot(db, target)
    assert decide(client, admin, target.id, "silencio_confirmado").json()["code"] == "silence_threshold_not_met"
    assert snapshot(db, target) == before


def test_a_light_alert_can_be_postponed_and_the_count_restarts(client, db):
    target = make_application(db)
    add_contacts(db, target, (3, "sin_respuesta"), (1, "sin_respuesta"))
    admin = login(client, ADMIN)
    assert decide(client, admin, target.id, "silencio_reprogramado", reason="Hablaremos la semana próxima").status_code == 201
    assert client.get(f"/api/v1/calls/{IA_CALL}/silence-review", headers=admin).json()["items"] == []
    assert stage_of(db, target) == "requisitos_en_revision"


def test_silence_creates_a_review_alert_and_never_closes_the_application(client, db):
    target, quiet = make_application(db), make_application(db)
    silent_for(db, target)
    add_contacts(db, quiet, (5, "sin_respuesta"))
    before = snapshot(db, target)
    review = client.get(f"/api/v1/calls/{IA_CALL}/silence-review", headers=login(client, SEL_IA))
    assert review.status_code == 200
    [item] = review.json()["items"]
    assert item["application_id"] == str(target.id) and item["codigo"] == target.codigo
    assert item["evidence"]["threshold_met"] is True and item["evidence"]["unanswered_attempts"] == 4
    assert item["evidence"]["alert_level"] == "accion"
    # PO 19/11/2026: the alert identifies the person by name; the e-mail stays in the application file.
    assert item["display_name"] == db.get(Person, target.person_id).display_name
    assert {"email", "person"}.isdisjoint(item)
    assert stage_of(db, target) == "requisitos_en_revision"
    assert snapshot(db, target)[:3] == before[:3]  # reading the alert only adds its own audit row


def test_a_person_confirms_silence_and_the_evidence_is_frozen_with_the_decision(client, db):
    target = make_application(db)
    silent_for(db, target)
    response = decide(client, login(client, COORD), target.id, "silencio_confirmado", reason="Cuatro intentos sin respuesta")
    assert response.status_code == 201, response.text
    evidence = response.json()["evidence"]
    assert (evidence["unanswered_attempts"], evidence["silence_days"], evidence["silence_max_contacts"], evidence["threshold_met"]) == (4, 30, 4, True)
    assert response.json()["to_stage"] == "retirada"
    assert stage_of(db, target) == "retirada"
    assert decide(client, login(client, ADMIN), target.id, "silencio_confirmado").status_code == 409


def test_postponing_a_silence_review_restarts_the_count_and_keeps_the_stage(client, db):
    target = make_application(db)
    silent_for(db, target)
    admin = login(client, ADMIN)
    assert decide(client, admin, target.id, "silencio_reprogramado", reason="La persona pidió más tiempo").status_code == 201
    assert stage_of(db, target) == "requisitos_en_revision"
    assert client.get(f"/api/v1/calls/{IA_CALL}/silence-review", headers=admin).json()["items"] == []
    assert decide(client, admin, target.id, "silencio_confirmado").status_code == 409
    kinds = db.scalars(select(ApplicationEvent.tipo).where(ApplicationEvent.application_id == target.id).order_by(ApplicationEvent.occurred_at)).all()
    assert kinds.count("nota") == 1 and "cambio_etapa" not in kinds


def test_silence_review_with_several_applications_keeps_each_evidence_separate(client, db):
    silent_a, silent_b, postponed, answered, few = (make_application(db) for _ in range(5))
    silent_for(db, silent_a, attempts=4)
    silent_for(db, silent_b, attempts=6, days=40)
    silent_for(db, postponed)
    add_contacts(db, answered, *NOT_YET_SILENCE["the person answered after the unanswered attempts"])
    add_contacts(db, few, *NOT_YET_SILENCE["fewer attempts than the action threshold"])
    admin = login(client, ADMIN)
    # A postponement restarts only its own application's count, never another one's.
    assert decide(client, admin, postponed.id, "silencio_reprogramado", reason="La persona pidió más tiempo").status_code == 201
    items = client.get(f"/api/v1/calls/{IA_CALL}/silence-review", headers=admin).json()["items"]
    by_code = {i["codigo"]: i["evidence"] for i in items}
    assert set(by_code) == {silent_a.codigo, silent_b.codigo, few.codigo}
    assert {code: e["alert_level"] for code, e in by_code.items()} == {silent_a.codigo: "accion", silent_b.codigo: "accion", few.codigo: "leve"}
    assert by_code[silent_a.codigo]["unanswered_attempts"] == 4
    assert by_code[silent_b.codigo]["unanswered_attempts"] == 6
    assert by_code[silent_b.codigo]["days_without_response"] >= 40


class CountingRows(list):
    """A list that counts how many times it is iterated."""

    def __init__(self, rows):
        super().__init__(rows)
        self.iterations = 0

    def __iter__(self):
        self.iterations += 1
        return super().__iter__()


def test_silence_review_reads_contacts_and_decisions_once_whatever_the_number_of_applications(db):
    """Regression guard: re-filtering every record per application (quadratic) iterates the lists N times."""
    from app.modules.preselection.router import silence_review_items

    call = db.get(Call, IA_CALL)
    applications = [(make_application(db), "Persona Sintética") for _ in range(5)]
    for application, _ in applications:
        silent_for(db, application)
    ids = [a.id for a, _ in applications]
    events = CountingRows(db.scalars(select(ApplicationEvent).where(ApplicationEvent.application_id.in_(ids))))
    decisions = CountingRows([])
    items = silence_review_items(call, applications, events, decisions, utcnow())
    assert {i.application_id for i in items} == set(ids)
    assert all(i.evidence.unanswered_attempts == 4 for i in items)
    assert (events.iterations, decisions.iterations) == (1, 1)


# ---------- per-call policy ----------


def policy_url(call_id=IA_CALL) -> str:
    return f"/api/v1/calls/{call_id}/preselection-policy"


DEFAULT_POLICY = {"silence_days": 30, "silence_max_contacts": 4, "silence_warning_contacts": 2}
SHORT_POLICY = {"silence_days": 7, "silence_max_contacts": 2, "silence_warning_contacts": 1}


def test_default_policy_is_a_light_alert_at_2_attempts_and_action_at_4_attempts_and_30_days(client):
    for call_id in (IA_CALL, DATA_CALL, IA_CLOSED_CALL):
        assert client.get(policy_url(call_id), headers=login(client, ADMIN)).json() == DEFAULT_POLICY


@pytest.mark.parametrize("editor", [ADMIN, CAPT_IA])
def test_policy_is_editable_per_call_by_administration_and_captacion_of_the_program(client, db, editor):
    """PO decision 19/11/2026: administration and captación (inside its program) edit the policy."""
    assert client.put(policy_url(), json=SHORT_POLICY, headers=login(client, editor)).status_code == 200
    assert client.get(policy_url(), headers=login(client, SEL_IA)).json() == SHORT_POLICY
    assert client.get(policy_url(DATA_CALL), headers=login(client, ADMIN)).json() == DEFAULT_POLICY
    audit_row = db.scalar(select(AuditEvent).where(AuditEvent.action == "call.preselection_policy_updated"))
    assert audit_row.meta == {**{f"{k}_before": v for k, v in DEFAULT_POLICY.items()}, **SHORT_POLICY}


def test_other_profiles_and_other_programs_cannot_edit_the_policy(client):
    other = {"silence_days": 1, "silence_max_contacts": 1, "silence_warning_contacts": 1}
    for who in (CAPT_DATA, SEL_IA, COORD, DOCENTE, ASPIRANTE):
        response = client.put(policy_url(), json=other, headers=login(client, who))
        assert response.status_code == 403
    assert response.json()["code"] == "no_policy_permission" and "captación" in response.json()["detail"]
    assert client.put(policy_url(), json=other).status_code == 401
    assert client.get(policy_url(), headers=login(client, ADMIN)).json() == DEFAULT_POLICY


INVALID_POLICIES = [
    {**DEFAULT_POLICY, "silence_days": 0}, {**DEFAULT_POLICY, "silence_days": 366},
    {**DEFAULT_POLICY, "silence_max_contacts": 0}, {**DEFAULT_POLICY, "silence_max_contacts": 21},
    {**DEFAULT_POLICY, "silence_warning_contacts": 0}, {**DEFAULT_POLICY, "silence_warning_contacts": 5},  # light alert after the action one
    {**DEFAULT_POLICY, "silence_days": "treinta"}, {"silence_days": 30, "silence_max_contacts": 4}, {**DEFAULT_POLICY, "extra": 1},
]


@pytest.mark.parametrize("payload", INVALID_POLICIES)
def test_invalid_policies_are_rejected(client, payload):
    assert client.put(policy_url(), json=payload, headers=login(client, ADMIN)).status_code == 422
    assert client.get(policy_url(), headers=login(client, ADMIN)).json() == DEFAULT_POLICY


def test_a_shorter_policy_applies_only_to_its_call(client, db):
    admin = login(client, ADMIN)
    ia_app, data_app = make_application(db, IA_CALL), make_application(db, DATA_CALL)
    for target in (ia_app, data_app):
        add_contacts(db, target, (12, "sin_respuesta"), (10, "sin_respuesta"))
    client.put(policy_url(), json=SHORT_POLICY, headers=admin)
    ia_items = client.get(f"/api/v1/calls/{IA_CALL}/silence-review", headers=admin).json()["items"]
    data_items = client.get(f"/api/v1/calls/{DATA_CALL}/silence-review", headers=admin).json()["items"]
    assert [(i["codigo"], i["evidence"]["alert_level"]) for i in ia_items] == [(ia_app.codigo, "accion")]
    assert [(i["codigo"], i["evidence"]["alert_level"]) for i in data_items] == [(data_app.codigo, "leve")]


def test_changing_the_policy_does_not_rewrite_decisions_already_taken(client, db):
    target = make_application(db)
    silent_for(db, target)
    admin = login(client, ADMIN)
    assert decide(client, admin, target.id, "silencio_confirmado").status_code == 201
    assert client.put(policy_url(), json={"silence_days": 90, "silence_max_contacts": 10, "silence_warning_contacts": 5}, headers=admin).status_code == 200
    [item] = history(client, admin, target.id).json()["items"]
    assert (item["evidence"]["silence_days"], item["evidence"]["silence_max_contacts"]) == (30, 4)
    assert stage_of(db, target) == "retirada"


# ---------- contact attempt results ----------


def test_contact_results_are_stored_returned_and_only_allowed_on_contacts(client, db):
    target = make_application(db)
    headers = login(client, CAPT_IA)
    url = f"/api/v1/applications/{target.id}/events"
    sent = client.post(url, json={"tipo": "contacto", "canal": "telefono", "resultado": "sin_respuesta", "resumen": "Llamada sin respuesta"}, headers=headers)
    assert sent.status_code == 201 and sent.json()["resultado"] == "sin_respuesta"
    detail = client.get(f"/api/v1/applications/{target.id}", headers=headers).json()
    assert [e["resultado"] for e in detail["events"] if e["tipo"] == "contacto"] == ["sin_respuesta"]
    assert client.post(url, json={"tipo": "nota", "resultado": "respondida", "resumen": "Nota"}, headers=headers).status_code == 422
    assert client.post(url, json={"tipo": "contacto", "resultado": "otro", "resumen": "Contacto"}, headers=headers).status_code == 422


# ---------- audit ----------


def test_audit_keeps_ids_and_codes_but_never_the_free_text_reason(client, db):
    target = make_application(db)
    assert decide(client, login(client, CAPT_IA), target.id, "retirada_expresa", reason="Texto libre que no debe copiarse a la auditoría").status_code == 201
    row = db.scalar(select(AuditEvent).where(AuditEvent.action == "preselection.decided"))
    assert row.target_type == "application" and row.target_id == str(target.id) and "captacion" in row.actor_roles
    assert row.meta == {"codigo": target.codigo, "decision": "retirada_expresa", "from_stage": "requisitos_en_revision", "to_stage": "retirada"}
    assert "Texto libre" not in str(row.meta)


# ---------- database guarantees ----------

BAD_DECISION_ROWS = {
    "blank reason": {"reason": "   "},
    "unknown decision": {"decision": "admitida"},
    "unknown stage": {"to_stage": "inventada"},
}


@pytest.mark.parametrize("case", list(BAD_DECISION_ROWS))
def test_database_rejects_inconsistent_decision_rows(db, case):
    target = make_application(db)
    row = {"decision": "convocada", "from_stage": "enviada", "to_stage": "convocada", "reason": REASON, **BAD_DECISION_ROWS[case]}
    db.add(PreselectionDecision(application_id=target.id, actor_user_id=db.scalar(select(User.id)), evidence={}, **row))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_database_rejects_a_result_on_anything_but_a_contact(db):
    target = make_application(db)
    db.add(ApplicationEvent(application_id=target.id, tipo="nota", resultado="sin_respuesta", resumen="Nota"))
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


@pytest.mark.parametrize(("column", "value"), [("silence_days", 0), ("silence_days", 366), ("silence_max_contacts", 0), ("silence_max_contacts", 21), ("silence_warning_contacts", 0), ("silence_warning_contacts", 5)])
def test_database_rejects_out_of_range_policies(db, column, value):
    setattr(db.get(Call, IA_CALL), column, value)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_migration_0005_downgrades_to_0007_and_upgrades_again():
    cfg = Config(os.path.join(API_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(API_DIR, "alembic"))
    try:
        command.downgrade(cfg, "0007")
        tables = set(inspect(engine).get_table_names())
        assert "preselection_decision" not in tables
        assert {"automation_execution", "call_requirement", "requirement_review", "knowledge_document"} <= tables
        assert {"silence_days", "silence_max_contacts", "silence_warning_contacts"}.isdisjoint(c["name"] for c in inspect(engine).get_columns("call"))
        assert "resultado" not in {c["name"] for c in inspect(engine).get_columns("application_event")}
    finally:
        command.upgrade(cfg, "head")
    assert {"preselection_decision", "automation_execution", "call_requirement"} <= set(inspect(engine).get_table_names())
    assert {"silence_days", "silence_max_contacts", "silence_warning_contacts"} <= {c["name"] for c in inspect(engine).get_columns("call")}
