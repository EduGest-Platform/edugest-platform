"""KAN-207: existing sessions lose revoked academic scope in both assistant surfaces."""

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy import select, text

from app.core.config import settings
from app.core.db import SessionLocal, utcnow
from app.modules.assistant import router as assistant_router
from app.modules.identity.models import User
from app.modules.knowledge.ingest import run_ingest
from app.modules.learning.models import Enrollment
from app.modules.submissions.models import Submission
from tests.conftest import ADMIN, CODER, DOCENTE, SEL_IA, login

COHORT = "COH-IA"
OTHER = "COH-DATA"
QUESTION = "Si entrego el Recetario un día tarde, ¿me lo aceptan?"


@pytest.fixture
def documents(db, monkeypatch):
    monkeypatch.setattr(settings, "rag_embed", False)
    monkeypatch.setattr(assistant_router, "today", lambda: date(2026, 12, 1))
    db.execute(text("TRUNCATE knowledge_chunk, knowledge_document"))
    db.commit()
    run_ingest(db, settings.corpus_path)


def ask(client, token, cohort_id=None):
    body = {"question": QUESTION}
    if cohort_id is not None:
        body["cohort_id"] = cohort_id
    return client.post("/api/v1/assistant/ask", headers=token, json=body)


def tool_paths(cohort):
    return [f"/api/v1/tools/{tool}?cohort_id={cohort}"
            for tool in ("attendance-summary", "competency-progress", "pending-submissions")]


def submission_state(submission_id):
    with SessionLocal() as db:
        row = db.get(Submission, uuid.UUID(submission_id))
        return row.status, row.revision, row.reviewed_at, row.submitted_at, row.enrollment_id


def test_team_removal_and_readd_apply_to_existing_tokens_across_documents_and_data(client, db, documents):
    tokens = [login(client, DOCENTE), login(client, DOCENTE)]
    teacher_id = db.scalars(select(User.id).where(User.email == DOCENTE)).one()
    colleague_id = db.scalars(select(User.id).where(User.email == SEL_IA)).one()
    team_path = f"/api/v1/cohorts/{COHORT}/teaching-team"
    # Grant a colleague through the actual API before self-removal, preserving the last-teacher rule.
    assert client.put(f"{team_path}/{colleague_id}", headers=tokens[0]).status_code == 200
    assignment = client.post(f"/api/v1/cohorts/{COHORT}/assignments", headers=tokens[0], json={
        "title": "Synthetic live-scope assignment", "due_at": (utcnow() + timedelta(days=1)).isoformat(),
        "rubric": ["Synthetic observable criterion"],
    })
    assert assignment.status_code == 201
    enrollment = db.scalars(select(Enrollment).where(Enrollment.cohort_id == COHORT, Enrollment.estado == "activa")).first()
    assert enrollment is not None
    submitted = client.put(f"/api/v1/assignments/{assignment.json()['id']}/submissions/{enrollment.id}",
                           headers=tokens[0], json={"check_results": {"passed": 1, "total": 2}})
    assert submitted.status_code == 200
    submission_id = submitted.json()["id"]
    context = f"/api/v1/tools/submissions/{submission_id}"
    protected = tool_paths(COHORT) + [context]
    for token in tokens:
        answer = ask(client, token, COHORT)
        assert answer.status_code == 200 and answer.json()["status"] == "answered"
        for path in protected:
            assert client.get(path, headers=token).status_code == 200, path
    before = submission_state(submission_id)
    removed = client.delete(f"{team_path}/{teacher_id}", headers=tokens[0])
    assert removed.status_code == 200
    assert str(teacher_id) not in {member["user_id"] for member in removed.json()["members"]}
    for token in tokens:
        assert client.get("/api/v1/auth/me", headers=token).status_code == 200
        assert ask(client, token, COHORT).status_code == 403
        remaining = ask(client, token)
        assert remaining.status_code == 200 and remaining.json()["scope_cohorts"] == [OTHER]
        for path in protected:
            denied = client.get(path, headers=token)
            assert denied.status_code == 403, path
            assert assignment.json()["title"] not in denied.text
        for path in tool_paths(OTHER):
            assert client.get(path, headers=token).status_code == 200, path
        assert client.post(f"/api/v1/submissions/{submission_id}/review", headers=token,
                           json={"expected_revision": submitted.json()["revision"]}).status_code == 403
    assert submission_state(submission_id) == before
    # Restoring the grant also affects these same tokens, without another login.
    assert client.put(f"{team_path}/{teacher_id}", headers=login(client, ADMIN)).status_code == 200
    for token in tokens:
        assert ask(client, token, COHORT).status_code == 200
        assert client.get(context, headers=token).status_code == 200
    assert submission_state(submission_id) == before


def test_coder_withdrawal_removes_both_assistant_surfaces_without_logging_out(client, db, documents):
    tokens = [login(client, CODER), login(client, CODER)]
    user = db.scalars(select(User).where(User.email == CODER)).one()
    enrollment = db.scalars(select(Enrollment).where(Enrollment.person_id == user.person_id,
                                                    Enrollment.cohort_id == COHORT, Enrollment.estado == "activa")).one()
    for token in tokens:
        assert ask(client, token, COHORT).status_code == 200
        for path in tool_paths(COHORT):
            assert client.get(path, headers=token).status_code == 200, path
    # Fixture-only lifecycle change; this does not claim a withdrawal UI/API exists.
    enrollment.estado = "baja_voluntaria"
    db.commit()
    for token in tokens:
        assert client.get("/api/v1/auth/me", headers=token).status_code == 200
        assert ask(client, token, COHORT).status_code == 403
        assert ask(client, token).status_code == 403
        for path in tool_paths(COHORT):
            assert client.get(path, headers=token).status_code == 403, path
    db.expire_all()
    assert db.get(Enrollment, enrollment.id).estado == "baja_voluntaria"
