"""KAN-191 / KAN-204 / KAN-67: feedback drafts are versioned, traceable and published only by a teacher's approval."""

import json
from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.core.db import utcnow
from app.modules.audit.models import AuditEvent
from app.modules.feedback.models import FeedbackDraft
from app.modules.identity.models import RoleAssignment, User
from app.modules.learning.models import Enrollment
from app.modules.submissions.models import Submission
from tests.conftest import CODER, COORD, DOCENTE, login

COHORT = "COH-IA"
PRIVATE_URL = "https://example.test/private-portfolio"
RUBRIC = ["Lee y cumple el enunciado", "Pruebas automáticas en verde"]
EDITED = "Buen trabajo con la estructura. Revisa los dos casos límite que fallan y vuelve a entregar."


@pytest.fixture
def case(client, db):
    teacher = login(client, DOCENTE)
    coder_user = db.scalars(select(User).where(User.email == CODER)).one()
    enrollment = db.scalars(select(Enrollment).where(Enrollment.person_id == coder_user.person_id,
                                                    Enrollment.cohort_id == COHORT, Enrollment.estado == "activa")).one()
    assignment = client.post(f"/api/v1/cohorts/{COHORT}/assignments", headers=teacher, json={
        "title": "Ejercicio sintético de feedback", "due_at": (utcnow() + timedelta(days=1)).isoformat(), "rubric": RUBRIC})
    assert assignment.status_code == 201, assignment.text
    submission = client.put(f"/api/v1/assignments/{assignment.json()['id']}/submissions/{enrollment.id}", headers=teacher,
                            json={"portfolio_url": PRIVATE_URL, "check_results": {"passed": 7, "total": 10}})
    assert submission.status_code == 200, submission.text
    return SimpleNamespace(teacher=teacher, coder=login(client, CODER), assignment_id=assignment.json()["id"],
                           enrollment_id=enrollment.id, submission_id=submission.json()["id"],
                           revision=submission.json()["revision"])


def drafts_path(case):
    return f"/api/v1/submissions/{case.submission_id}/feedback-drafts"


def published_path(case):
    return f"/api/v1/submissions/{case.submission_id}/feedback"


def test_generated_draft_is_labelled_and_never_published(client, db, case):
    draft = client.post(drafts_path(case), headers=case.teacher)
    assert draft.status_code == 201, draft.text
    body = draft.json()
    assert body["source"] == "template" and body["status"] == "draft" and body["version"] == 1
    assert "sin IA generativa" in body["label"] and "pendiente de revisión docente" in body["label"]
    assert "7 de 10" in body["body"] and all(criterion in body["body"] for criterion in RUBRIC)
    assert body["rubric"] == RUBRIC and body["check_results"] == {"passed": 7, "total": 10}  # provenance
    assert PRIVATE_URL not in draft.text  # never the portfolio URL or submitted content

    coder_view = client.get(published_path(case), headers=case.coder)
    assert coder_view.status_code == 200 and coder_view.json()["feedback"] is None
    assert body["body"] not in coder_view.text
    assert client.get(drafts_path(case), headers=case.coder).status_code == 403
    db.expire_all()
    assert db.get(Submission, case.submission_id).status == "submitted"  # generating never reviews or publishes


def test_edit_creates_a_new_version_and_keeps_the_old(client, case):
    first = client.post(drafts_path(case), headers=case.teacher).json()
    edited = client.put(f"/api/v1/feedback-drafts/{first['id']}", headers=case.teacher, json={"body": EDITED, "expected_version": 1})
    assert edited.status_code == 201, edited.text
    assert edited.json()["version"] == 2 and edited.json()["source"] == "teacher" and edited.json()["body"] == EDITED

    items = client.get(drafts_path(case), headers=case.teacher).json()["items"]
    assert [i["version"] for i in items] == [1, 2] and items[0]["body"] == first["body"]  # history kept
    stale = client.put(f"/api/v1/feedback-drafts/{first['id']}", headers=case.teacher, json={"body": "Otro texto", "expected_version": 1})
    assert stale.status_code == 409 and stale.json()["code"] == "feedback_outdated"


def test_only_teacher_approval_publishes_and_is_recorded(client, db, case):
    first = client.post(drafts_path(case), headers=case.teacher).json()
    edited = client.put(f"/api/v1/feedback-drafts/{first['id']}", headers=case.teacher, json={"body": EDITED, "expected_version": 1}).json()
    assert client.post(f"/api/v1/feedback-drafts/{first['id']}/approve", headers=case.teacher,
                       json={"expected_revision": case.revision}).status_code == 409  # not the latest version

    approved = client.post(f"/api/v1/feedback-drafts/{edited['id']}/approve", headers=case.teacher, json={"expected_revision": case.revision})
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "approved" and approved.json()["approved_at"]
    again = client.post(f"/api/v1/feedback-drafts/{edited['id']}/approve", headers=case.teacher, json={"expected_revision": case.revision})
    assert again.status_code == 409 and again.json()["code"] == "feedback_already_approved"

    published = client.get(published_path(case), headers=case.coder).json()["feedback"]
    assert published["body"] == EDITED and published["version"] == 2 and "aprobado" in published["label"]
    teacher_id = db.scalars(select(User.id).where(User.email == DOCENTE)).one()
    assert db.get(FeedbackDraft, edited["id"]).approved_by == teacher_id

    events = list(db.scalars(select(AuditEvent).where(AuditEvent.action.like("feedback.%")).order_by(AuditEvent.id)))
    assert [e.action for e in events] == ["feedback.draft_generated", "feedback.draft_edited", "feedback.approved"]
    assert all(EDITED not in json.dumps(e.meta, ensure_ascii=False) for e in events)  # ids and versions, never the text


def test_resubmission_makes_old_drafts_stale(client, case):
    draft = client.post(drafts_path(case), headers=case.teacher).json()
    resubmitted = client.put(f"/api/v1/assignments/{case.assignment_id}/submissions/{case.enrollment_id}", headers=case.coder,
                             json={"portfolio_url": PRIVATE_URL + "-v2"})
    assert resubmitted.status_code == 200, resubmitted.text
    new_revision = resubmitted.json()["revision"]
    assert new_revision == case.revision + 1
    for revision in (case.revision, new_revision):
        stale = client.post(f"/api/v1/feedback-drafts/{draft['id']}/approve", headers=case.teacher, json={"expected_revision": revision})
        assert stale.status_code == 409 and stale.json()["code"] == "feedback_stale"
    # The new artifact has no test results yet, so there is nothing to base a draft on.
    missing = client.post(drafts_path(case), headers=case.teacher)
    assert missing.status_code == 409 and missing.json()["code"] == "feedback_without_results"


def test_staff_without_review_permission_and_coders_cannot_draft(client, db, case):
    coord = login(client, COORD)
    assert client.post(drafts_path(case), headers=coord).status_code == 403
    assert client.post(drafts_path(case), headers=case.coder).status_code == 403
    assert client.get(published_path(case), headers=coord).status_code == 403

    teacher_id = db.scalars(select(User.id).where(User.email == DOCENTE)).one()
    db.query(RoleAssignment).filter(RoleAssignment.user_id == teacher_id, RoleAssignment.scope_id == COHORT).delete()
    db.commit()
    assert client.post(drafts_path(case), headers=login(client, DOCENTE)).status_code == 403
