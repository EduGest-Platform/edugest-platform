"""KAN-144: a real call-to-selection preserves history; live scopes govern historical reads."""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.db import SessionLocal, utcnow
from app.main import app
from app.modules.admissions.models import Application, ApplicationEvent
from app.modules.identity.models import RoleAssignment, User
from app.modules.preselection.models import PreselectionDecision
from app.modules.requirements.models import RequirementReviewRevision
from tests.conftest import ADMIN, CAPT_DATA, CAPT_IA, SEL_IA, login

CALL = "CONV-IA-2027A"
REF = "synthetic-handoff-v1"


@pytest.fixture
def handoff(client, db):
    admin = login(client, ADMIN)
    application = db.scalar(select(Application).where(Application.call_id == CALL,
                                                      Application.stage.in_(["enviada", "requisitos_en_revision"])))
    assert application is not None
    base = f"/api/v1/applications/{application.id}"
    definition = client.post(f"/api/v1/calls/{CALL}/requirements", headers=admin,
                             json={"ref": REF, "code": "synthetic-handoff", "label": "Synthetic handoff document", "kind": "required"})
    assert definition.status_code == 201, definition.text
    recruiter = login(client, CAPT_IA)
    contact = client.post(base + "/events", headers=recruiter,
                          json={"tipo": "contacto", "canal": "telefono", "resultado": "respondida",
                                "resumen": "Synthetic contact before call to selection"})
    assert contact.status_code == 201
    review = client.put(base + f"/requirement-reviews/{REF}", headers=recruiter,
                        json={"result": "not_met", "reason": "Synthetic evidence before handoff"})
    assert review.status_code == 201, review.text
    before = client.get(base, headers=admin).json()
    history = client.get(base + f"/requirement-reviews/{REF}/history", headers=admin).json()
    return application.id, base, before, history, contact.json(), review.json()


def call_to_selection(client, base):
    response = client.post(base + "/preselection-decisions", headers=login(client, SEL_IA),
                           json={"decision": "convocada", "reason": "Synthetic human handoff to selection"})
    assert response.status_code == 201, response.text
    return response.json()


def test_new_session_preserves_dossier_contact_and_review_after_human_handoff(client, db, handoff):
    application_id, base, before, old_history, contact, review = handoff
    decision = call_to_selection(client, base)
    assert decision["evidence"]["unresolved_requirement_reviews"] == 1
    with TestClient(app) as fresh:
        selector = login(fresh, SEL_IA)
        dossier = fresh.get(base, headers=selector)
        assert dossier.status_code == 200
        after = dossier.json()
        for key in ("id", "codigo", "call_id", "person", "motivacion", "disponibilidad", "created_at"):
            assert after[key] == before[key], key
        assert after["stage"] == "convocada"
        assert after["events"][:len(before["events"])] == before["events"]
        original_contact = next(event for event in after["events"] if event["id"] == contact["id"])
        assert original_contact == contact
        assert original_contact["actor"] == review["reviewer"]
        assert fresh.get(base + f"/requirement-reviews/{REF}/history", headers=selector).json() == old_history
        decisions = fresh.get(base + "/preselection-decisions", headers=selector).json()["items"]
        assert decisions == [decision]
    with SessionLocal() as verification:
        assert verification.get(Application, application_id).stage == "convocada"
        assert verification.scalar(select(func.count()).select_from(PreselectionDecision)
                                   .where(PreselectionDecision.application_id == application_id)) == 1


def test_selection_amendment_keeps_original_review_author_reason_and_time(client, db, handoff):
    application_id, base, _, old_history, _, first = handoff
    call_to_selection(client, base)
    selector = login(client, SEL_IA)
    amended = client.put(base + f"/requirement-reviews/{REF}", headers=selector,
                         json={"result": "met", "reason": "Synthetic new evidence reviewed by selection", "expected_version": 1})
    assert amended.status_code == 200, amended.text
    assert amended.json()["id"] == first["id"] and amended.json()["version"] == 2
    assert amended.json()["reviewer"] != first["reviewer"]
    history = client.get(base + f"/requirement-reviews/{REF}/history", headers=selector).json()
    assert history["items"][:1] == old_history["items"]
    assert [row["result"] for row in history["items"]] == ["not_met", "met"]
    with SessionLocal() as verification:
        assert verification.get(Application, application_id).stage == "convocada"
        assert verification.scalar(select(func.count()).select_from(RequirementReviewRevision)
                                   .where(RequirementReviewRevision.review_id == uuid.UUID(first["id"]))) == 2


@pytest.mark.parametrize("email", [CAPT_IA, SEL_IA])
def test_revocation_applies_to_existing_token_without_erasing_history(client, db, handoff, email):
    application_id, base, _, _, _, _ = handoff
    call_to_selection(client, base)
    active_token = login(client, email)
    paths = (base, base + "/requirement-reviews", base + f"/requirement-reviews/{REF}/history",
             base + "/preselection-decisions")
    before = {path: client.get(path, headers=active_token).json() for path in paths}
    assert all(client.get(path, headers=active_token).status_code == 200 for path in paths)
    crm_count = db.scalar(select(func.count()).select_from(ApplicationEvent))
    user_id = db.scalar(select(User.id).where(User.email == email))
    assignments = db.scalars(select(RoleAssignment).where(RoleAssignment.user_id == user_id,
                                                          RoleAssignment.revoked_at.is_(None))).all()
    assert assignments
    for assignment in assignments:
        assignment.revoked_at = utcnow()
    db.commit()
    # Authentication survives; authorization must be reloaded for every request.
    assert client.get("/api/v1/auth/me", headers=active_token).status_code == 200
    for path in paths:
        assert client.get(path, headers=active_token).status_code == 403, path
    assert client.post(base + "/events", headers=active_token,
                       json={"tipo": "nota", "resumen": "Synthetic denied write"}).status_code == 403
    admin = login(client, ADMIN)
    assert {path: client.get(path, headers=admin).json() for path in paths} == before
    db.expire_all()
    assert db.get(Application, application_id).stage == "convocada"
    assert db.scalar(select(func.count()).select_from(ApplicationEvent)) == crm_count


def test_call_to_selection_does_not_expand_foreign_staff_scope(client, handoff):
    _, base, _, _, _, _ = handoff
    outsider = login(client, CAPT_DATA)
    paths = (base, base + "/requirement-reviews", base + f"/requirement-reviews/{REF}/history",
             base + "/preselection-decisions")
    for path in paths:
        assert client.get(path, headers=outsider).status_code == 403
    call_to_selection(client, base)
    for path in paths:
        assert client.get(path, headers=outsider).status_code == 403
