"""HTTP evidence for cohort activation and its downstream academic records."""

import pytest
from sqlalchemy import select

from app.modules.audit.models import AuditEvent
from app.modules.catalog.models import Cohort
from app.modules.competencies.models import CohortCompetencyFramework
from app.modules.identity.models import User
from tests.conftest import ADMIN, ASPIRANTE, CODER, DOCENTE, login
from tests.test_attendance import ONLINE, UNJUSTIFIED, put
from tests.test_learner_enrollments import own_seed_enrollment
from tests.test_competencies import COHORT, assign, published_tree


def test_publication_and_assignment_are_separate_audited_actions(client, db):
    teacher = login(client, DOCENTE)
    admin = login(client, ADMIN)
    base = db.get(Cohort, COHORT)
    sibling = Cohort(
        id="COH-IA-SIBLING", program_id=base.program_id, call_id=base.call_id,
        nombre="Synthetic parallel cohort", inicio=base.inicio, fin=base.fin,
    )
    db.add(sibling)
    db.commit()

    framework = published_tree(client, teacher, codes=("C1",))
    own_path = f"/api/v1/cohorts/{COHORT}/competencies"
    sibling_path = f"/api/v1/cohorts/{sibling.id}/competencies"
    assert client.get(own_path, headers=teacher).json()["framework"] is None
    assert assign(client, teacher, framework["id"], cohort=sibling.id).status_code == 403
    attached = assign(client, teacher, framework["id"])
    assert attached.status_code == 200, attached.text
    assert attached.json()["framework"]["id"] == framework["id"]
    assert client.get(sibling_path, headers=admin).json()["framework"] is None

    link = db.get(CohortCompetencyFramework, COHORT)
    teacher_id = db.scalar(select(User.id).where(User.email == DOCENTE))
    assert str(link.framework_id) == framework["id"]
    assert link.assigned_by == teacher_id and link.assigned_at is not None
    events = db.scalars(select(AuditEvent).where(AuditEvent.action.in_([
        "competencies.framework_published", "competencies.cohort_framework_assigned",
    ])).order_by(AuditEvent.id)).all()
    assert [(event.action, event.target_id) for event in events] == [
        ("competencies.framework_published", framework["id"]),
        ("competencies.cohort_framework_assigned", COHORT),
    ]
    assert all(event.actor_user_id == teacher_id and event.at is not None for event in events)


HELD_DATE = "2026-09-14"


@pytest.fixture
def half_day_record(client, db):
    teacher = login(client, DOCENTE)
    enrollment = own_seed_enrollment(db)
    path = f"/api/v1/cohorts/{enrollment.cohort_id}/attendance-sessions"
    for shift in ("tarde", "manana"):
        session = client.post(path, headers=teacher, json={"session_date": HELD_DATE, "shift": shift})
        assert session.status_code == 201, session.text
    morning_id = session.json()["id"]
    recorded = put(client, teacher, morning_id, enrollment.id, UNJUSTIFIED)
    assert recorded.status_code == 200, recorded.text
    return teacher, enrollment, morning_id


def test_attendance_correction_reaches_the_learner_without_filling_missing_sessions(client, half_day_record):
    teacher, enrollment, morning_id = half_day_record
    path = f"/api/v1/me/enrollments/{enrollment.id}/attendance"
    window = {"date_from": HELD_DATE, "date_to": HELD_DATE}
    owner = login(client, CODER)
    before = client.get(path, headers=owner, params=window)
    assert before.status_code == 200, before.text
    assert before.json()["totals"]["unjustified_absence_days"] == 0.5
    assert before.json()["totals"]["unrecorded_days"] == 0.5
    assert before.json()["totals"]["attendance_rate"] == 0

    reason = "Synthetic reason retained only in the correction history"
    corrected = put(client, teacher, morning_id, enrollment.id, {**ONLINE, "reason": reason})
    assert corrected.status_code == 200 and corrected.json()["version"] == 2
    revision_path = f"/api/v1/attendance-records/{corrected.json()['id']}/revisions"
    revisions = client.get(revision_path, headers=teacher)
    assert revisions.status_code == 200 and revisions.json()["items"][-1]["reason"] == reason

    after = client.get(path, headers=login(client, CODER), params=window)
    assert after.status_code == 200 and reason not in after.text
    totals = after.json()["totals"]
    assert totals["attended_online_days"] == 0.5 and totals["unjustified_absence_days"] == 0
    assert totals["unrecorded_days"] == 0.5 and totals["attendance_rate"] == 1
    assert client.get(path, headers=login(client, ASPIRANTE), params=window).status_code == 404
