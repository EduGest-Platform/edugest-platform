"""KAN-272: optional next action on CRM contacts (what, who, by when)."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.modules.admissions import next_actions
from app.modules.admissions.models import ApplicationEvent
from app.modules.audit.models import AuditEvent
from app.modules.identity.models import RoleAssignment, User
from tests.conftest import ASPIRANTE, CAPT_DATA, CAPT_IA, CODER, COORD, SEL_IA, login, new_application


@pytest.fixture
def dossier(client):
    receipt = client.post("/api/v1/applications", json=new_application()).json()
    return f"/api/v1/applications/{receipt['id']}"


def user_id(db, email):
    return str(db.scalar(select(User.id).where(User.email == email)))


def contact(next_action=None, tipo="contacto"):
    body = {"tipo": tipo, "canal": "telefono", "resumen": "Synthetic operational summary"}
    if next_action is not None:
        body["next_action"] = next_action
    return body


def action(owner_id, description="Synthetic follow-up call", days=3):
    return {"description": description, "owner_user_id": owner_id, "due_on": str(next_actions.today() + timedelta(days=days))}


def test_next_action_is_stored_shown_as_current_and_kept_out_of_the_audit(client, db, dossier):
    headers = login(client, CAPT_IA)
    owner = user_id(db, SEL_IA)
    created = client.post(f"{dossier}/events", headers=headers, json=contact(action(owner, "  Call back  ", days=0)))
    assert created.status_code == 201, created.text
    assert created.json()["next_action"]["description"] == "Call back"
    assert created.json()["next_action"]["owner_user_id"] == owner

    detail = client.get(dossier, headers=headers).json()
    assert detail["next_action"] == created.json()["next_action"]
    assert detail["events"][-1]["actor"] and detail["events"][-1]["occurred_at"]
    audited = db.scalar(select(AuditEvent).where(AuditEvent.action == "application.event_added"))
    assert "Call back" not in str(audited.meta)


def test_the_latest_next_action_wins_and_a_plain_contact_does_not_clear_it(client, db, dossier):
    headers = login(client, CAPT_IA)
    owner = user_id(db, CAPT_IA)
    for body in (contact(action(owner, "First")), contact(action(owner, "Second")), contact()):
        assert client.post(f"{dossier}/events", headers=headers, json=body).status_code == 201
    detail = client.get(dossier, headers=headers).json()
    assert detail["next_action"]["description"] == "Second"
    assert [e["next_action"]["description"] for e in detail["events"] if e["next_action"]] == ["First", "Second"]


@pytest.mark.parametrize("missing", ["description", "owner_user_id", "due_on"])
def test_an_incomplete_next_action_is_rejected(client, db, dossier, missing):
    partial = action(user_id(db, CAPT_IA))
    del partial[missing]
    response = client.post(f"{dossier}/events", headers=login(client, CAPT_IA), json=contact(partial))
    assert response.status_code == 422


@pytest.mark.parametrize("change", [{"description": "   "}, {"description": "x" * 201}, {"due_on": "2000-01-01"}])
def test_invalid_values_are_rejected(client, db, dossier, change):
    body = contact({**action(user_id(db, CAPT_IA)), **change})
    assert client.post(f"{dossier}/events", headers=login(client, CAPT_IA), json=body).status_code == 422


@pytest.mark.parametrize("tipo", ["nota", "recordatorio"])
def test_only_contacts_take_a_next_action(client, db, dossier, tipo):
    body = contact(action(user_id(db, CAPT_IA)), tipo=tipo)
    assert client.post(f"{dossier}/events", headers=login(client, CAPT_IA), json=body).status_code == 422


@pytest.mark.parametrize("email", [CAPT_DATA, COORD, CODER])
def test_owner_needs_the_crm_permission_on_this_call(client, db, dossier, email):
    body = contact(action(user_id(db, email)))
    assert client.post(f"{dossier}/events", headers=login(client, CAPT_IA), json=body).status_code == 422
    assert db.scalar(select(ApplicationEvent).where(ApplicationEvent.next_action.is_not(None))) is None


def test_revoked_or_inactive_staff_cannot_own_a_next_action(client, db, dossier):
    headers = login(client, CAPT_IA)
    selector = db.scalar(select(User).where(User.email == SEL_IA))
    selector.is_active = False
    db.commit()
    assert client.post(f"{dossier}/events", headers=headers, json=contact(action(str(selector.id)))).status_code == 422
    selector.is_active = True
    for assignment in db.scalars(select(RoleAssignment).where(RoleAssignment.user_id == selector.id)):
        assignment.revoked_at = assignment.created_at
    db.commit()
    assert client.post(f"{dossier}/events", headers=headers, json=contact(action(str(selector.id)))).status_code == 422


def test_owner_list_only_offers_staff_with_crm_access(client, db, dossier):
    offered = {row["user_id"] for row in client.get(f"{dossier}/crm-owners", headers=login(client, CAPT_IA)).json()}
    assert {user_id(db, CAPT_IA), user_id(db, SEL_IA)} <= offered
    assert offered.isdisjoint({user_id(db, e) for e in (CAPT_DATA, COORD, CODER)})


@pytest.mark.parametrize("email,expected", [(CAPT_DATA, 403), (COORD, 403), (CODER, 403), (None, 401)])
def test_outsiders_cannot_list_owners_or_write_a_next_action(client, db, dossier, email, expected):
    headers = login(client, email) if email else {}
    assert client.get(f"{dossier}/crm-owners", headers=headers).status_code == expected
    body = contact(action(user_id(db, CAPT_IA)))
    assert client.post(f"{dossier}/events", headers=headers, json=body).status_code == expected


def test_the_applicant_never_sees_the_next_action(client, db):
    applicant = login(client, ASPIRANTE)
    receipt = client.post("/api/v1/applications", json=new_application(email=ASPIRANTE), headers=applicant).json()
    dossier = f"/api/v1/applications/{receipt['id']}"
    body = contact(action(user_id(db, CAPT_IA), "Staff only follow-up"))
    assert client.post(f"{dossier}/events", headers=login(client, CAPT_IA), json=body).status_code == 201
    mine = client.get("/api/v1/me/applications", headers=applicant)
    assert [row["codigo"] for row in mine.json()] == [receipt["codigo"]]
    assert "Staff only follow-up" not in mine.text and "next_action" not in mine.text
    assert client.get(dossier, headers=applicant).status_code == 403


def test_the_database_refuses_a_partial_next_action(client, db, dossier):
    application_id = dossier.rsplit("/", 1)[1]
    db.add(ApplicationEvent(application_id=application_id, tipo="contacto", resumen="Synthetic", next_action="Half"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_a_person_account_is_never_an_owner_even_with_a_crm_role(client, db, dossier):
    coder = db.scalar(select(User).where(User.email == CODER))
    assert coder.person_id is not None
    db.add(RoleAssignment(user_id=coder.id, role="captacion", scope_type="program", scope_id="P-IA"))
    db.commit()
    headers = login(client, CAPT_IA)
    offered = {row["user_id"] for row in client.get(f"{dossier}/crm-owners", headers=headers).json()}
    assert str(coder.id) not in offered
    assert client.post(f"{dossier}/events", headers=headers, json=contact(action(str(coder.id)))).status_code == 422


@pytest.mark.parametrize("utc_now,yesterday,madrid_today", [
    (datetime(2026, 11, 25, 23, 30, tzinfo=UTC), "2026-11-25", "2026-11-26"),
    (datetime(2026, 7, 1, 22, 30, tzinfo=UTC), "2026-07-01", "2026-07-02"),
])
def test_the_deadline_boundary_follows_madrid_not_utc(client, db, dossier, monkeypatch, utc_now, yesterday, madrid_today):
    class FrozenClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return utc_now.astimezone(tz)

    headers = login(client, CAPT_IA)
    owner = user_id(db, CAPT_IA)
    monkeypatch.setattr(next_actions, "datetime", FrozenClock)
    for due_on, expected in ((yesterday, 422), (madrid_today, 201)):
        body = contact({"description": "Synthetic", "owner_user_id": owner, "due_on": due_on})
        assert client.post(f"{dossier}/events", headers=headers, json=body).status_code == expected


@pytest.mark.parametrize("tipo,description", [("nota", "Synthetic"), ("contacto", "   ")])
def test_the_database_refuses_a_complete_but_invalid_next_action(client, db, dossier, tipo, description):
    owner = db.scalar(select(User.id).where(User.email == CAPT_IA))
    db.add(ApplicationEvent(
        application_id=dossier.rsplit("/", 1)[1], tipo=tipo, resumen="Synthetic", next_action=description,
        next_action_owner_id=owner, next_action_due_on=next_actions.today(),
    ))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
