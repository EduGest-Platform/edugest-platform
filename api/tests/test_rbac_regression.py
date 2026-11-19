"""KAN-109: F1 authorization regressions against disposable synthetic PostgreSQL."""

import uuid

import pytest
from sqlalchemy import func, select

from app.core.db import utcnow
from app.modules.admissions.models import Application, ApplicationEvent
from app.modules.audit.models import AuditEvent
from app.modules.identity.models import RoleAssignment, User
from tests.conftest import ADMIN, ASPIRANTE, CAPT_DATA, CAPT_IA, CODER, COORD, DOCENTE, SEL_IA, login, new_application
from tests.test_rbac import an_app


def event_count(db, application_id):
    return db.scalar(select(func.count()).select_from(ApplicationEvent).where(ApplicationEvent.application_id == uuid.UUID(application_id)))


@pytest.mark.parametrize("invalid_token", [None, "Bearer synthetic-invalid-token"])
def test_protected_f1_routes_reject_anonymous_and_invalid_tokens(client, invalid_token):
    application = an_app(client, "P-IA")
    headers = {"Authorization": invalid_token} if invalid_token else {}
    routes = [
        ("GET", "/api/v1/applications"),
        ("GET", f"/api/v1/applications/{application['id']}"),
        ("POST", f"/api/v1/applications/{application['id']}/events"),
        ("GET", "/api/v1/me/applications"),
        ("GET", "/api/v1/calls/CONV-IA-2027A/summary"),
        ("GET", "/api/v1/audit-events"),
    ]
    for method, path in routes:
        response = client.request(method, path, headers=headers, **({"json": {"tipo": "nota", "resumen": "Synthetic note"}} if method == "POST" else {}))
        assert response.status_code == 401, (method, path, response.status_code)


@pytest.mark.parametrize("account,foreign_program", [(CAPT_IA, "P-DATA"), (SEL_IA, "P-DATA"), (CAPT_DATA, "P-IA")])
def test_foreign_crm_write_has_no_event_or_success_audit_side_effect(client, db, account, foreign_program):
    application = an_app(client, foreign_program)
    headers = login(client, account)
    before = event_count(db, application["id"])
    response = client.post(f"/api/v1/applications/{application['id']}/events", headers=headers, json={"tipo": "nota", "resumen": "Forbidden synthetic note"})
    assert response.status_code == 404  # out of scope looks like an unknown id (PO decision 19/11/2026)
    assert event_count(db, application["id"]) == before
    assert db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action == "application.event_added", AuditEvent.target_id == application["id"])) == 0


@pytest.mark.parametrize("account", [ASPIRANTE, CODER, DOCENTE, COORD])
def test_unprivileged_roles_cannot_spoof_admin_headers_or_create_events(client, db, account):
    application = an_app(client, "P-IA")
    headers = {**login(client, account), "X-Role": "admin", "X-Scope-Type": "global"}
    before = event_count(db, application["id"])
    response = client.post(f"/api/v1/applications/{application['id']}/events", headers=headers, json={"tipo": "nota", "resumen": "Synthetic spoof", "role": "admin"})
    assert response.status_code == 403
    assert event_count(db, application["id"]) == before
    assert client.get("/api/v1/audit-events", headers=headers).status_code == 403


@pytest.mark.parametrize("account,own_call,foreign_call", [(CAPT_IA, "CONV-IA-2027A", "CONV-DATA-2027A"), (SEL_IA, "CONV-IA-2027A", "CONV-DATA-2027A"), (CAPT_DATA, "CONV-DATA-2027A", "CONV-IA-2027A")])
def test_query_parameters_cannot_broaden_scope_or_expose_foreign_aggregates(client, account, own_call, foreign_call):
    headers = login(client, account)
    response = client.get("/api/v1/applications", headers=headers, params={"role": "admin", "scope_type": "global", "limit": 200})
    assert response.status_code == 200
    assert response.json()["items"]
    assert {item["call_id"] for item in response.json()["items"]} == {own_call}
    assert client.get(f"/api/v1/calls/{own_call}/summary", headers=headers).status_code == 200
    assert client.get(f"/api/v1/calls/{foreign_call}/summary", headers=headers).status_code == 403


def test_revoked_assignment_takes_effect_on_existing_session(client, db):
    application = an_app(client, "P-IA")
    headers = login(client, CAPT_IA)
    assert client.get(f"/api/v1/applications/{application['id']}", headers=headers).status_code == 200
    user = db.scalar(select(User).where(User.email == CAPT_IA))
    assignments = list(db.scalars(select(RoleAssignment).where(RoleAssignment.user_id == user.id)))
    assert assignments
    for assignment in assignments:
        assignment.revoked_at = utcnow()
    db.commit()
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200
    assert client.get("/api/v1/applications", headers=headers).status_code == 403
    before = event_count(db, application["id"])
    assert client.post(f"/api/v1/applications/{application['id']}/events", headers=headers, json={"tipo": "nota", "resumen": "After revocation"}).status_code == 403
    assert event_count(db, application["id"]) == before


def test_deactivated_account_loses_access_on_existing_session(client, db):
    headers = login(client, ADMIN)
    assert client.get("/api/v1/audit-events", headers=headers).status_code == 200
    user = db.scalar(select(User).where(User.email == ADMIN))
    user.is_active = False
    db.commit()
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert client.get("/api/v1/audit-events", headers=headers).status_code == 401


def test_crm_actor_is_server_derived_even_with_forged_payload(client, db):
    application = an_app(client, "P-IA")
    admin = db.scalar(select(User).where(User.email == ADMIN))
    staff = db.scalar(select(User).where(User.email == CAPT_IA))
    response = client.post(f"/api/v1/applications/{application['id']}/events", headers=login(client, CAPT_IA), json={"tipo": "nota", "resumen": "Synthetic actor check", "actor_user_id": str(admin.id), "actor": "admin"})
    assert response.status_code == 201
    assert response.json()["actor"] == staff.display_name
    event = db.get(ApplicationEvent, uuid.UUID(response.json()["id"]))
    assert event.actor_user_id == staff.id
    assert event.actor_user_id != admin.id


def test_self_view_cannot_be_redirected_to_another_person_or_leak_notes(client, db):
    headers = login(client, ASPIRANTE)
    user = db.scalar(select(User).where(User.email == ASPIRANTE))
    # A-001 is a browser-only draft in the seed; submit it through the public API.
    created = client.post("/api/v1/applications", headers=headers, json=new_application(email=user.email))
    assert created.status_code == 201
    own = list(db.scalars(select(Application).where(Application.person_id == user.person_id)))
    assert own
    application = own[0]
    marker = "Synthetic internal-only note"
    assert client.post(f"/api/v1/applications/{application.id}/events", headers=login(client, ADMIN), json={"tipo": "nota", "resumen": marker}).status_code == 201
    foreign = an_app(client, "P-DATA")
    response = client.get("/api/v1/me/applications", headers=headers, params={"person_id": foreign["person"]["id"], "application_id": foreign["id"], "role": "admin"})
    assert response.status_code == 200
    assert {item["id"] for item in response.json()} == {str(item.id) for item in own}
    assert marker not in response.text
    for item in response.json():
        assert set(item) == {"id", "codigo", "call_id", "call_nombre", "stage", "created_at", "updated_at"}
