"""HTTP evidence for cohort activation and its downstream academic records."""

import pytest
from sqlalchemy import func, select

from app.core.config import settings

from app.modules.audit.models import AuditEvent
from app.modules.catalog.models import Cohort
from app.modules.competencies.models import CohortCompetencyFramework
from app.modules.identity.models import User
from app.modules.learning.models import Enrollment
from tests.conftest import ADMIN, ASPIRANTE, CODER, COORD, DOCENTE, login
from tests.test_attendance import ONLINE, UNJUSTIFIED, put
from tests.test_learner_enrollments import own_seed_enrollment
from tests.test_submissions import new_assignment, review, submit
from tests.test_competencies import COHORT, assess, assign, published_tree


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


@pytest.fixture
def assessed_framework(client, db):
    teacher = login(client, DOCENTE)
    enrollment = own_seed_enrollment(db)
    framework = published_tree(client, teacher, codes=("C1",))
    attached = assign(client, teacher, framework["id"], cohort=enrollment.cohort_id)
    assert attached.status_code == 200, attached.text
    competency_id = framework["competencies"][0]["id"]
    recorded = assess(client, teacher, enrollment.id, competency_id, 2, evidence="Synthetic level two evidence")
    assert recorded.status_code == 201, recorded.text
    return teacher, enrollment, framework, recorded.json()


def test_new_publication_preserves_assigned_levels_until_explicit_reassignment(client, assessed_framework):
    teacher, enrollment, first, assessment = assessed_framework
    owner = login(client, CODER)
    learner_path = f"/api/v1/me/enrollments/{enrollment.id}/competencies"
    staff_path = f"/api/v1/enrollments/{enrollment.id}/assessments"
    baseline = client.get(learner_path, headers=owner)
    assert baseline.status_code == 200 and baseline.json()["current"][0]["level"] == 2

    second = published_tree(client, teacher, codes=("C1",))
    still_assigned = client.get(learner_path, headers=owner)
    assert still_assigned.status_code == 200 and still_assigned.json() == baseline.json()
    premature = assess(client, teacher, enrollment.id, second["competencies"][0]["id"], 3)
    assert premature.status_code == 409 and premature.json()["code"] == "competency_not_in_cohort"

    assert assign(client, teacher, second["id"], cohort=enrollment.cohort_id).status_code == 200
    stale = assess(client, teacher, enrollment.id, first["competencies"][0]["id"], 3)
    assert stale.status_code == 409 and stale.json()["code"] == "competency_not_in_cohort"
    updated = client.get(learner_path, headers=owner).json()
    current, = updated["current"]
    assert updated["framework_version"] == second["version"]
    assert current["competency_id"] == second["competencies"][0]["id"] and current["level"] is None
    history = client.get(staff_path, headers=teacher)
    assert history.status_code == 200 and history.json()["history"] == [assessment]


def test_overview_applies_attendance_window_and_keeps_other_indicators_current(
    client, db, monkeypatch, half_day_record, assessed_framework,
):
    teacher, enrollment, morning_id = half_day_record
    _, _, framework, _ = assessed_framework
    coordinator = login(client, COORD)
    cohort_size = db.scalar(select(func.count()).select_from(Enrollment).where(
        Enrollment.cohort_id == enrollment.cohort_id, Enrollment.estado != "baja_voluntaria",
    ))
    assert cohort_size > 0
    monkeypatch.setattr(settings, "min_group_size", cohort_size)
    assignment = new_assignment(client, teacher, cohort_id=enrollment.cohort_id)
    link = "https://example.test/synthetic-overview-delivery"
    submitted = submit(client, login(client, CODER), assignment["id"], enrollment.id, portfolio_url=link)
    assert submitted.status_code == 200, submitted.text
    assert review(client, teacher, submitted.json()).status_code == 200

    path = f"/api/v1/cohorts/{enrollment.cohort_id}/progress-overview"
    window = {"attendance_from": HELD_DATE, "attendance_to": HELD_DATE}
    baseline = client.get(path, headers=coordinator, params=window)
    assert baseline.status_code == 200 and baseline.headers["cache-control"] == "no-store"
    first = baseline.json()
    assert first["aggregate_only"] is True
    assert first["attendance"]["totals"]["unjustified_absence_days"] == 0.5
    assert first["competencies"]["framework_version"] == framework["version"]
    assert first["competencies"]["distribution"][0]["counts"]["level_2"] == 1
    delivery, = first["submissions"]["assignments"]
    assert delivery["assignment_id"] == assignment["id"] and delivery["counts"]["reviewed"] == 1
    assert str(enrollment.id) not in baseline.text and link not in baseline.text

    fixed = put(client, teacher, morning_id, enrollment.id, {**ONLINE, "reason": "Synthetic attendance correction"})
    assert fixed.status_code == 200, fixed.text
    response = client.get(path, headers=coordinator, params=window)
    assert response.status_code == 200
    totals = response.json()["attendance"]["totals"]
    assert totals["attended_days"] == 0.5 and totals["unjustified_absence_days"] == 0
    assert totals["attendance_rate"] == 1

    other_day = {"attendance_from": "2026-09-15", "attendance_to": "2026-09-15"}
    outside = client.get(path, headers=coordinator, params=other_day)
    assert outside.status_code == 200
    outside_body = outside.json()
    assert outside_body["attendance"]["has_data"] is False
    assert outside_body["attendance"]["totals"]["attendance_rate"] is None
    assert outside_body["competencies"] == first["competencies"]
    assert outside_body["submissions"]["assignments"] == [delivery]

    monkeypatch.setattr(settings, "min_group_size", cohort_size + 1)
    filtered = client.get(path, headers=coordinator, params=window)
    assert filtered.status_code == 200
    hidden = filtered.json()
    assert all(hidden[section]["has_data"] is None for section in ("attendance", "competencies", "submissions"))
    assert hidden["attendance"]["totals"]["attendance_rate"] is None
    assert hidden["competencies"]["distribution"][0]["counts"] is None
    assert hidden["submissions"]["assignments"][0]["counts"] is None
