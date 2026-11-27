from sqlalchemy import select

from app.modules.audit.models import AuditEvent
from app.modules.identity.models import Person, RoleAssignment, User
from app.modules.learning.models import Enrollment
from tests.conftest import CODER, COORD, DOCENTE, login
from tests.test_risk_evidence_models import evidence

PATH = "/api/v1/cohorts/COH-IA/risk-alerts"


def setup_alert(db, cohort):
    enrollment = db.scalar(select(Enrollment).where(Enrollment.cohort_id == cohort))
    alert = evidence(db, enrollment_id=enrollment.id)
    db.add(alert)
    db.commit()
    return alert, enrollment


def test_human_review_has_a_history_and_never_changes_enrollment(client, db):
    alert, enrollment = setup_alert(db, "COH-IA")
    initial = enrollment.estado
    teacher = login(client, DOCENTE)
    path = f"{PATH}/{alert.id}"
    response = client.get(PATH, headers=teacher, params={"state": "pending"})
    assert response.status_code == 200 and response.json()["total"] == 1
    assert response.json()["items"][0]["experimental_support_signal"] is None
    note = "Synthetic tutor support note"
    first = client.post(path + "/interventions", headers=teacher,
                        json={"kind": "support", "note": note, "expected_state": "pending"})
    assert first.status_code == 201 and first.json()["review_state"] == "in_review"
    assert first.json()["assigned_to"]
    stale = client.post(path + "/interventions", headers=teacher,
                        json={"kind": "closure", "note": note, "expected_state": "pending"})
    assert stale.status_code == 409
    after_stale = client.get(path, headers=teacher).json()
    assert after_stale['review_state'] == 'in_review'
    assert [row['kind'] for row in after_stale['interventions']] == ['support']
    closed = client.post(path + "/interventions", headers=teacher,
                         json={"kind": "closure", "note": note, "expected_state": "in_review"})
    assert closed.status_code == 201 and closed.json()["review_state"] == "closed"
    history = client.get(path, headers=teacher).json()
    assert [row["kind"] for row in history["interventions"]] == ["support", "closure"]
    assert all(row["actor"] for row in history["interventions"])
    assert client.get(PATH, headers=teacher, params={"state": "pending"}).json()["total"] == 0
    db.refresh(enrollment)
    assert enrollment.estado == initial
    assert all(note not in str(event.meta) for event in db.scalars(select(AuditEvent)))


def test_cohort_scope_and_synthetic_boundary(client, db):
    own, _ = setup_alert(db, "COH-IA")
    foreign, enrollment = setup_alert(db, "COH-DATA")
    owner_id = db.scalar(select(User.id).where(User.email == DOCENTE))
    db.query(RoleAssignment).filter(RoleAssignment.user_id == owner_id, RoleAssignment.scope_id == "COH-DATA").delete()
    db.commit()
    teacher = login(client, DOCENTE)
    assert client.get(PATH).status_code == 401
    for account in (COORD, CODER):
        assert client.get(PATH, headers=login(client, account)).status_code == 403
    assert client.get("/api/v1/cohorts/COH-DATA/risk-alerts", headers=teacher).status_code == 403
    assert client.get(f"{PATH}/{foreign.id}", headers=teacher).status_code == 404
    assert client.post(f"{PATH}/{foreign.id}/interventions", headers=teacher,
                       json={"kind": "closure", "note": "Synthetic", "expected_state": "pending"}).status_code == 404
    assert client.post(f"{PATH}/{own.id}/interventions", headers=teacher,
                       json={"kind": "expel", "note": "Synthetic", "expected_state": "pending"}).status_code == 422
    db.get(Person, enrollment.person_id).is_synthetic = False
    db.commit()
    admin = login(client, "admin@gistar.example")
    assert client.get("/api/v1/cohorts/COH-DATA/risk-alerts", headers=admin).json()["total"] == 0
