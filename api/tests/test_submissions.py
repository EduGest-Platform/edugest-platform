"""KAN-56: assignments with deadline, one submission per coder, late / double delivery, review and cohort scope."""

from datetime import timedelta

import pytest
from sqlalchemy import func, select

from app.core.db import utcnow
from app.modules.audit.models import AuditEvent
from app.modules.learning.models import Enrollment
from app.modules.submissions.models import Submission
from tests.conftest import CAPT_IA, CODER, COORD, DOCENTE, login

COHORT, OTHER = "COH-IA", "COH-DATA"


@pytest.fixture
def teacher(client):
    return login(client, DOCENTE)


def enrollment_of(db, cohort_id=COHORT) -> str:
    return str(db.scalar(select(Enrollment.id).where(Enrollment.cohort_id == cohort_id).order_by(Enrollment.created_at, Enrollment.id)))


def new_assignment(client, headers, cohort_id=COHORT, due_in_days=7, **over) -> dict:
    body = {"title": "Actividad sintética", "due_at": (utcnow() + timedelta(days=due_in_days)).isoformat(), "rubric": ["solución", "pruebas"]}
    body.update(over)
    r = client.post(f"/api/v1/cohorts/{cohort_id}/assignments", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


def submit(client, headers, assignment_id, enrollment_id, **body):
    return client.put(f"/api/v1/assignments/{assignment_id}/submissions/{enrollment_id}", json=body, headers=headers)


def states(client, headers, enrollment_id) -> dict[str, str]:
    r = client.get(f"/api/v1/enrollments/{enrollment_id}/submissions", headers=headers)
    assert r.status_code == 200, r.text
    return {item["assignment_id"]: item["state"] for item in r.json()["items"]}


def test_pending_then_on_time_then_reviewed(client, db, teacher):
    a = new_assignment(client, teacher)
    enrollment = enrollment_of(db)
    assert states(client, teacher, enrollment)[a["id"]] == "pending"
    r = submit(client, teacher, a["id"], enrollment, portfolio_url="https://example.test/repo", check_results={"passed": 8, "total": 10})
    assert r.status_code == 200, r.text
    assert r.json()["late"] is False and r.json()["status"] == "submitted"
    assert states(client, teacher, enrollment)[a["id"]] == "on_time"
    reviewed = client.post(f"/api/v1/submissions/{r.json()['id']}/review", headers=teacher)
    assert reviewed.status_code == 200 and reviewed.json()["status"] == "reviewed"
    actions = set(db.scalars(select(AuditEvent.action).where(AuditEvent.target_id == r.json()["id"])))
    assert {"submission.create", "submission.review"} <= actions


def test_missing_after_deadline_is_overdue_and_late_delivery_is_late(client, db, teacher):
    a = new_assignment(client, teacher, due_in_days=-2)
    enrollment = enrollment_of(db)
    assert states(client, teacher, enrollment)[a["id"]] == "overdue"
    r = submit(client, teacher, a["id"], enrollment)
    assert r.status_code == 200 and r.json()["late"] is True
    assert states(client, teacher, enrollment)[a["id"]] == "late"


def test_resubmission_keeps_one_row_and_the_first_date_until_reviewed(client, db, teacher):
    a = new_assignment(client, teacher)
    enrollment = enrollment_of(db)
    first = submit(client, teacher, a["id"], enrollment, portfolio_url="https://example.test/v1").json()
    second = submit(client, teacher, a["id"], enrollment, portfolio_url="https://example.test/v2").json()
    assert first["id"] == second["id"] and second["portfolio_url"].endswith("v2")
    assert second["first_submitted_at"] == first["first_submitted_at"]
    assert db.scalar(select(func.count()).select_from(Submission).where(Submission.assignment_id == a["id"])) == 1
    client.post(f"/api/v1/submissions/{first['id']}/review", headers=teacher)
    closed = submit(client, teacher, a["id"], enrollment)
    assert closed.status_code == 409 and closed.json()["code"] == "submission_reviewed"


@pytest.mark.parametrize("url", ["http://example.test/repo", "ftp://x", "javascript:alert(1)", "https://"])
def test_portfolio_url_must_be_https(client, db, teacher, url):
    a = new_assignment(client, teacher)
    assert submit(client, teacher, a["id"], enrollment_of(db), portfolio_url=url).status_code == 422


def test_portfolio_url_is_optional(client, db, teacher):
    a = new_assignment(client, teacher)
    r = submit(client, teacher, a["id"], enrollment_of(db), portfolio_url="  ")
    assert r.status_code == 200 and r.json()["portfolio_url"] is None


def test_deadline_without_time_zone_is_rejected(client, teacher):
    r = client.post(f"/api/v1/cohorts/{COHORT}/assignments", json={"title": "Sin zona", "due_at": "2026-12-01T23:59:00"}, headers=teacher)
    assert r.status_code == 422


def test_enrollment_from_another_cohort_cannot_deliver(client, db, teacher):
    a = new_assignment(client, teacher)
    r = submit(client, teacher, a["id"], enrollment_of(db, OTHER))
    assert r.status_code in (403, 409)


def test_draft_assignment_is_hidden_and_closed(client, db, teacher):
    a = new_assignment(client, teacher, status="draft")
    listed = client.get(f"/api/v1/cohorts/{COHORT}/assignments", headers=teacher).json()["items"]
    assert a["id"] not in {x["id"] for x in listed}
    assert submit(client, teacher, a["id"], enrollment_of(db)).status_code == 409


@pytest.mark.parametrize("account", [CAPT_IA, COORD, CODER])
def test_non_teachers_cannot_read_or_write_per_person_submissions(client, db, teacher, account):
    a = new_assignment(client, teacher)
    enrollment = enrollment_of(db)
    other = login(client, account)
    assert client.get(f"/api/v1/enrollments/{enrollment}/submissions", headers=other).status_code == 403
    assert client.get(f"/api/v1/cohorts/{COHORT}/assignments", headers=other).status_code == 403
    assert submit(client, other, a["id"], enrollment).status_code == 403
    assert client.post(f"/api/v1/cohorts/{COHORT}/assignments", json={"title": "x" * 5, "due_at": utcnow().isoformat()}, headers=other).status_code == 403

