import uuid
from datetime import timedelta

from sqlalchemy import func, select

from app.core.db import utcnow
from app.modules.admissions.models import Application
from app.modules.audit.models import AuditEvent
from app.modules.selection.models import SelectionAppointment, SelectionDecision
from tests.conftest import ADMIN, ASPIRANTE, CAPT_IA, SEL_IA, login
from tests.test_selection_decisions import DATA_CALL, make_application


def path(application):
    return f"/api/v1/applications/{application.id}/selection-appointments"


def future(days=1):
    return (utcnow() + timedelta(days=days)).isoformat()


def schedule(client, app, headers, **changes):
    return client.post(path(app), headers=headers, json={
        "kind": "individual_interview", "scheduled_at": future(), "location": "Sala sintética",
        **changes,
    })


def move_into_past(db, appointment_id):
    db.get(SelectionAppointment, uuid.UUID(appointment_id)).scheduled_at = utcnow() - timedelta(minutes=1)
    db.commit()


def test_individual_interview_second_opportunity_preserves_human_decision_boundary(client, db):
    app = make_application(db, stage="convocada")
    selector = login(client, SEL_IA)
    before = db.scalar(select(func.count()).select_from(SelectionDecision))
    first = schedule(client, app, selector)
    assert first.status_code == 201
    first_id = first.json()["id"]
    first_outcome = f"{path(app)}/{first_id}/outcome"
    assert client.post(first_outcome, headers=selector, json={"result": "no_show"}).status_code == 409
    move_into_past(db, first_id)
    assert client.post(first_outcome, headers=selector, json={"result": "no_show", "assessment": "Texto"}).status_code == 422
    absent = client.post(first_outcome, headers=selector, json={"result": "no_show"})
    assert absent.status_code == 200 and absent.json()["state"] == "no_show"
    assert client.post(first_outcome, headers=selector, json={"result": "attended"}).status_code == 409

    second = schedule(client, app, selector, previous_id=first_id)
    assert second.status_code == 201 and second.json()["previous_id"] == first_id
    assert schedule(client, app, selector, previous_id=first_id, scheduled_at=future(2)).status_code == 409
    second_id = second.json()["id"]
    move_into_past(db, second_id)
    result = client.post(f"{path(app)}/{second_id}/outcome", headers=selector, json={
        "result": "attended", "conclusions": "  Síntesis de entrevista  ", "assessment": "Valoración de prueba",
    })
    assert result.status_code == 200 and result.json()["conclusions"] == "Síntesis de entrevista"

    view = client.get(path(app), headers=selector).json()
    assert view["can_edit"] is True
    assert {item["kind"] for item in view["items"]} == {"individual_interview"}
    assert {item["state"] for item in view["items"]} == {"no_show", "attended"}
    db.expire_all()
    assert db.get(Application, app.id).stage == "convocada"
    assert db.scalar(select(func.count()).select_from(SelectionDecision)) == before
    outcomes = db.scalars(select(AuditEvent).where(
        AuditEvent.target_id == str(app.id), AuditEvent.action == "selection.appointment_outcome_recorded",
    )).all()
    assert {row.meta.get("result") for row in outcomes} == {"attended", "no_show"}
    assert all(set(row.meta) == {"appointment_id", "result"} for row in outcomes)


def test_rescheduling_and_scope_checks(client, db):
    target = make_application(db, stage="evaluacion_en_curso")
    other = make_application(db, call_id=DATA_CALL, stage="convocada")
    selector, admin = login(client, SEL_IA), login(client, ADMIN)
    missing = f"/api/v1/applications/{uuid.uuid4()}/selection-appointments"
    for unauthorized in [login(client, ASPIRANTE), login(client, CAPT_IA)]:
        assert client.get(path(target), headers=unauthorized).status_code == 403
        assert client.get(missing, headers=unauthorized).status_code == 403
    assert client.get(path(other), headers=selector).status_code == 403
    assert schedule(client, other, selector).status_code == 403
    assert schedule(client, target, selector, scheduled_at="2027-03-01T12:00:00").status_code == 422
    assert schedule(client, target, selector, scheduled_at=(utcnow() - timedelta(days=1)).isoformat()).status_code == 422

    first = schedule(client, target, selector, kind="group_day")
    assert first.status_code == 201
    first_id = first.json()["id"]
    assert schedule(client, target, selector, kind="group_day").status_code == 409
    assert schedule(client, other, admin, kind="group_day", previous_id=first_id).status_code == 404
    assert schedule(client, target, selector, kind="individual_interview", previous_id=first_id).status_code == 409
    replacement = schedule(client, target, selector, kind="group_day", previous_id=first_id, scheduled_at=future(2))
    assert replacement.status_code == 201
    assert schedule(client, target, selector, kind="group_day", previous_id=first_id, scheduled_at=future(3)).status_code == 409
    records = client.get(path(target), headers=selector).json()["items"]
    assert [(row["id"], row["state"]) for row in records] == [
        (replacement.json()["id"], "scheduled"), (first_id, "rescheduled"),
    ]

    target.stage = "retirada"
    db.commit()
    assert client.get(path(target), headers=selector).json()["can_edit"] is False
    assert schedule(client, target, selector).status_code == 409


def test_outcome_cannot_cross_dossiers_or_programs(client, db):
    target = make_application(db, stage="convocada")
    sibling = make_application(db, stage="convocada")
    foreign = make_application(db, call_id=DATA_CALL, stage="convocada")
    selector, admin = login(client, SEL_IA), login(client, ADMIN)
    created = schedule(client, target, selector)
    assert created.status_code == 201, created.text
    appointment_id = created.json()["id"]
    move_into_past(db, appointment_id)
    body = {"result": "attended", "assessment": "Synthetic assessment"}
    for app, headers, status in ((sibling, selector, 404), (foreign, selector, 403), (foreign, admin, 404)):
        response = client.post(f"{path(app)}/{appointment_id}/outcome", headers=headers, json=body)
        assert response.status_code == status, response.text
    db.expire_all()
    appointment = db.get(SelectionAppointment, uuid.UUID(appointment_id))
    assert appointment.state == "scheduled"
    assert appointment.recorded_at is None and appointment.assessment is None
    response = client.post(f"{path(target)}/{appointment_id}/outcome", headers=selector, json=body)
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "attended"
