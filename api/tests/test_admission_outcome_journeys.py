"""KAN-182: HTTP journeys from public intake through human outcomes, on real PostgreSQL."""

import uuid
from datetime import date

import pytest
from sqlalchemy import func, select

from app.modules.admissions.models import Application, ApplicationEvent
from app.modules.audit.models import AuditEvent
from app.modules.catalog.models import Call, Cohort
from app.modules.learning.models import Enrollment
from app.modules.preselection.models import PreselectionDecision
from app.modules.selection.models import SelectionDecision
from tests.conftest import CAPT_DATA, CAPT_IA, CODER, SEL_IA, login, new_application

CALL = "CONV-IA-2027A"
COHORT = "COH-JOURNEY"
REASON = "Synthetic human review for the outcome journey"


def request(client, method, path, actor=None, body=None, expected=200):
    response = client.request(method, f"/api/v1{path}", headers=actor or {}, json=body)
    assert response.status_code == expected, response.text
    return response.json()


@pytest.fixture
def intake(client, db):
    # Reference data only: never assign an application stage or create a decision/enrollment directly.
    admitted = db.scalar(select(func.count()).select_from(Application).where(
        Application.call_id == CALL, Application.stage == "admitida",
    ))
    db.get(Call, CALL).plazas = admitted + 5
    db.add(Cohort(id=COHORT, call_id=CALL, program_id="P-IA", nombre="Synthetic journey cohort",
                  inicio=date(2027, 3, 1), fin=date(2027, 9, 30)))
    db.commit()
    receipt = request(client, "POST", "/applications", body=new_application(
        email="outcome.journey@example.test",
    ), expected=201)
    assert receipt["stage"] == "enviada"
    actor = login(client, CAPT_IA)
    path = f"/applications/{receipt['id']}"
    contact = request(client, "POST", f"{path}/events", actor, {
        "tipo": "contacto", "canal": "telefono", "resultado": "respondida",
        "resumen": "Synthetic contact before selection",
    }, expected=201)
    return receipt, path, contact, actor


def invite(client, path, actor):
    invitation = request(client, "POST", f"{path}/preselection-decisions", actor, {
        "decision": "convocada", "reason": REASON,
    }, expected=201)
    assert (invitation["from_stage"], invitation["to_stage"]) == ("enviada", "convocada")
    return invitation


def decide(client, path, actor, outcome, expected=201):
    body = {"decision": outcome, "reason": REASON}
    if outcome == "admitida":
        body["cohort_id"] = COHORT
    return request(client, "POST", f"{path}/selection-decisions", actor, body, expected)


def persisted(db, receipt):
    """Inspect durable state without bypassing the endpoints to drive the journey."""
    db.expire_all()
    app_id = uuid.UUID(receipt["id"])
    return (
        db.get(Application, app_id).stage,
        list(db.scalars(select(Enrollment).where(Enrollment.application_id == app_id))),
        list(db.scalars(select(SelectionDecision).where(SelectionDecision.application_id == app_id))),
    )


def mutation_snapshot(db, receipt):
    db.expire_all()
    app_id = uuid.UUID(receipt["id"])
    result = [db.get(Application, app_id).stage]
    for model in (Enrollment, SelectionDecision, PreselectionDecision, ApplicationEvent):
        result.append(set(db.scalars(select(model.id).where(model.application_id == app_id))))
    result.append(set(db.scalars(select(AuditEvent.id).where(
        AuditEvent.target_id == receipt["id"],
        AuditEvent.action.in_(["preselection.decided", "selection.decided"]),
    ))))
    return result


@pytest.mark.parametrize("outcome", ["admitida", "lista_espera", "retirada_expresa"])
def test_public_intake_reaches_only_the_explicit_human_outcome(client, db, intake, outcome):
    receipt, path, contact, recruitment = intake
    invitation = invite(client, path, recruitment)
    selector = login(client, SEL_IA)
    stage, enrollments, decisions = persisted(db, receipt)
    assert stage == "convocada" and enrollments == decisions == []

    if outcome == "retirada_expresa":
        result = request(client, "POST", f"{path}/preselection-decisions", recruitment, {
            "decision": outcome, "reason": REASON,
        }, expected=201)
        assert result["to_stage"] == "retirada"
        stage, enrollments, decisions = persisted(db, receipt)
        assert stage == "retirada" and enrollments == decisions == []
        before = mutation_snapshot(db, receipt)
        assert decide(client, path, selector, "admitida", 409)["code"] == "application_withdrawn"
        assert mutation_snapshot(db, receipt) == before
    else:
        result = decide(client, path, selector, outcome)
        stage, enrollments, decisions = persisted(db, receipt)
        assert stage == outcome and len(decisions) == 1
        assert result["from_stage"] == "convocada" and result["to_stage"] == outcome
        if outcome == "admitida":
            assert len(enrollments) == 1
            enrollment = enrollments[0]
            application = db.get(Application, uuid.UUID(receipt["id"]))
            assert enrollment.person_id == application.person_id
            assert (enrollment.cohort_id, enrollment.estado) == (COHORT, "activa")
            assert str(enrollment.id) == result["enrollment_id"]
            before = mutation_snapshot(db, receipt)
            assert decide(client, path, selector, outcome, 409)["code"] == "selection_ended"
            assert mutation_snapshot(db, receipt) == before
        else:
            assert enrollments == [] and result["enrollment_id"] is None
            overview = request(client, "GET", f"/calls/{CALL}/selection-overview", selector)
            assert receipt["id"] in {row["application_id"] for row in overview["waiting_list"]}

    # A later outcome never discards the contact or the original invitation.
    history = request(client, "GET", f"{path}/preselection-decisions", recruitment)
    assert history["items"][0]["id"] == invitation["id"]
    dossier = request(client, "GET", path, selector)
    assert contact["id"] in {event["id"] for event in dossier["events"]}
    rows = list(db.scalars(select(AuditEvent).where(
        AuditEvent.target_id == receipt["id"],
        AuditEvent.action.in_(["preselection.decided", "selection.decided"]),
    )))
    assert len(rows) == 2 and all(row.actor_user_id and row.at for row in rows)
    assert all(REASON not in str(row.meta) and "reason" not in row.meta for row in rows)


def test_waiting_intake_is_enrolled_once_only_after_a_later_human_promotion(client, db, intake):
    receipt, path, _, recruitment = intake
    invite(client, path, recruitment)
    selector = login(client, SEL_IA)
    decide(client, path, selector, "lista_espera")
    assert persisted(db, receipt)[1] == []
    promoted = decide(client, path, selector, "admitida")
    assert promoted["from_stage"] == "lista_espera"
    assert len(persisted(db, receipt)[1]) == 1
    history = request(client, "GET", f"{path}/selection-decisions", selector)
    assert [row["decision"] for row in history["items"]] == ["lista_espera", "admitida"]
    overview = request(client, "GET", f"/calls/{CALL}/selection-overview", selector)
    assert receipt["id"] not in {row["application_id"] for row in overview["waiting_list"]}


def test_real_intake_cannot_be_advanced_or_enrolled_by_unauthorised_profiles(client, db, intake):
    receipt, path, _, recruitment = intake
    before = mutation_snapshot(db, receipt)
    foreign = login(client, CAPT_DATA)
    request(client, "POST", f"{path}/preselection-decisions", foreign, {
        "decision": "convocada", "reason": REASON,
    }, expected=403)
    assert mutation_snapshot(db, receipt) == before
    selector = login(client, SEL_IA)
    assert decide(client, path, selector, "admitida", 409)["code"] == "selection_not_started"
    assert mutation_snapshot(db, receipt) == before
    invite(client, path, recruitment)
    for actor in (recruitment, login(client, CODER), None):
        before = mutation_snapshot(db, receipt)
        decide(client, path, actor, "admitida", 403 if actor else 401)
        assert mutation_snapshot(db, receipt) == before
    assert persisted(db, receipt)[1] == []
