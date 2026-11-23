"""KAN-214: terminated sessions cannot read private data or drive workflow writes."""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.db import SessionLocal, utcnow
from app.core.security import token_hash
from app.modules.admissions.models import Application, ApplicationEvent
from app.modules.audit.models import AuditEvent
from app.modules.identity.models import AuthSession, User
from app.modules.learning.models import Enrollment
from app.modules.preselection.models import PreselectionDecision
from app.modules.selection.models import SelectionDecision
from tests.conftest import ADMIN, login, new_application


def state(application_id):
    with SessionLocal() as db:
        app_id = uuid.UUID(application_id)
        result = [db.get(Application, app_id).stage]
        for model in (ApplicationEvent, Enrollment, PreselectionDecision, SelectionDecision):
            result.append(set(db.scalars(select(model.id).where(model.application_id == app_id))))
        result.append(set(db.scalars(select(AuditEvent.id).where(
            AuditEvent.target_id == application_id,
            AuditEvent.action.in_(["application.event_added", "preselection.decided", "selection.decided"]),
        ))))
        return result


@pytest.mark.parametrize("termination", ["expired", "logout", "inactive_account"])
def test_session_termination_blocks_private_reads_and_writes_on_all_admission_layers(client, db, termination):
    receipt = client.post("/api/v1/applications", json=new_application(email="session.boundary@example.test"))
    assert receipt.status_code == 201
    application_id = receipt.json()["id"]
    path = f"/api/v1/applications/{application_id}"
    actor = login(client, ADMIN)
    sibling = login(client, ADMIN)
    reads = [
        "/api/v1/auth/me", "/api/v1/applications", path,
        path + "/requirement-reviews", path + "/preselection-decisions", path + "/selection-decisions",
        "/api/v1/calls/CONV-IA-2027A/silence-review", "/api/v1/audit-events",
    ]
    # Prove the routes exist and this actor can read them before invalidation.
    for route in reads:
        assert client.get(route, headers=actor).status_code == 200, route

    if termination == "logout":
        assert client.post("/api/v1/auth/logout", headers=actor).status_code == 204
    elif termination == "expired":
        digest = token_hash(actor["Authorization"].removeprefix("Bearer "))
        session = db.scalars(select(AuthSession).where(AuthSession.token_hash == digest)).one()
        session.expires_at = utcnow() - timedelta(seconds=1)
        db.commit()
    else:
        user = db.scalars(select(User).where(User.email == ADMIN)).one()
        user.is_active = False
        db.commit()

    before = state(application_id)
    for route in reads:
        response = client.get(route, headers=actor)
        assert response.status_code == 401, route
        assert response.headers.get("www-authenticate", "").lower() == "bearer"
        assert "session.boundary@example.test" not in response.text
    writes = [
        (path + "/events", {"tipo": "nota", "resumen": "Synthetic denied note"}),
        (path + "/preselection-decisions", {"decision": "convocada", "reason": "Synthetic denied invitation"}),
        (path + "/selection-decisions", {"decision": "lista_espera", "reason": "Synthetic denied decision"}),
    ]
    for route, body in writes:
        assert client.post(route, headers=actor, json=body).status_code == 401, route
    assert state(application_id) == before
    # Session logout/expiry is local to that token; disabling a user affects every session.
    expected = 401 if termination == "inactive_account" else 200
    assert client.get(path, headers=sibling).status_code == expected
