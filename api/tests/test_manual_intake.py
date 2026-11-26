"""KAN-275: selection and coordination register applications that arrive outside the public form."""

import os
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.core.db import SessionLocal
from app.main import app
from app.modules.admissions.models import MANUAL_ORIGINS, Application, ApplicationEvent, IdentityReview
from app.modules.admissions.schemas import ApplicationCreate
from app.modules.admissions.service import create_application
from app.modules.audit.models import AuditEvent
from app.modules.catalog.models import Call
from app.modules.identity.models import Person, RoleAssignment, User
from tests.conftest import API_DIR, ADMIN, ASPIRANTE, CAPT_DATA, CAPT_IA, CODER, COORD, DOCENTE, SEL_IA, login, new_application

IA_CALL, DATA_CALL, CLOSED_CALL = "CONV-IA-2027A", "CONV-DATA-2027A", "CONV-IA-2026B"
URL = "/api/v1/manual-intake/applications"
CALLS_URL = "/api/v1/manual-intake/calls"
EMAIL = "nueva.persona@example.test"


def manual(**over) -> dict:
    body = new_application()
    del body["acepta_datos_sinteticos"]
    body.update(origin_channel="telefono", confirma_datos_sinteticos=True)
    body.update(over)
    return body


def applications(db) -> int:
    db.expire_all()
    return db.scalar(select(func.count()).select_from(Application))


def user_id(db, email):
    return db.scalar(select(User.id).where(User.email == email))


def stored(db, receipt) -> Application:
    db.expire_all()
    return db.scalar(select(Application).where(Application.id == receipt["id"]))


@pytest.mark.parametrize("account", [SEL_IA, COORD, ADMIN])
def test_selection_coordination_and_admin_register_in_scope(client, db, account):
    response = client.post(URL, headers=login(client, account), json=manual())
    assert response.status_code == 201, response.text
    assert set(response.json()) == {"id", "codigo", "call_id", "stage", "created_at"}
    application = stored(db, response.json())
    assert application.origin_channel == "telefono" and application.created_by == user_id(db, account)
    assert application.created_at is not None and application.stage == "enviada"


@pytest.mark.parametrize("account", [CAPT_IA, CAPT_DATA, DOCENTE, ASPIRANTE, CODER])
def test_other_profiles_get_403_for_known_and_unknown_calls(client, db, account):
    headers = login(client, account)
    before = applications(db)
    for call_id in (IA_CALL, DATA_CALL, "NO-EXISTE"):
        assert client.post(URL, headers=headers, json=manual(call_id=call_id)).status_code == 403
    assert client.get(CALLS_URL, headers=headers).status_code == 403
    assert applications(db) == before


def test_a_call_outside_scope_is_refused_audited_and_leaves_nothing(client, db):
    before, people = applications(db), db.scalar(select(func.count()).select_from(Person))
    sequence = db.get(Call, DATA_CALL).next_seq
    response = client.post(URL, headers=login(client, SEL_IA), json=manual(call_id=DATA_CALL))
    assert response.status_code == 403 and "no la tienes asignada" in response.json()["detail"]
    assert applications(db) == before
    assert db.scalar(select(func.count()).select_from(Person)) == people
    assert db.get(Call, DATA_CALL).next_seq == sequence
    denied, = db.scalars(select(AuditEvent).where(AuditEvent.action == "application.manual_intake_denied")).all()
    assert denied.target_id == DATA_CALL and denied.actor_user_id == user_id(db, SEL_IA) and not denied.meta


def test_a_revoked_assignment_no_longer_registers(client, db):
    from app.core.db import utcnow

    headers = login(client, SEL_IA)
    assignment = db.scalar(select(RoleAssignment).where(RoleAssignment.user_id == user_id(db, SEL_IA)))
    assignment.revoked_at = utcnow()
    db.commit()
    assert client.post(URL, headers=headers, json=manual()).status_code == 403


def test_the_route_needs_a_session(client):
    assert client.post(URL, json=manual()).status_code == 401
    assert client.get(CALLS_URL).status_code == 401


def test_the_call_list_follows_scope_and_the_public_intake_rule(client, db):
    assert [c["id"] for c in client.get(CALLS_URL, headers=login(client, SEL_IA)).json()] == [IA_CALL]
    everything = login(client, COORD)
    assert {c["id"] for c in client.get(CALLS_URL, headers=everything).json()} == {IA_CALL, DATA_CALL}
    db.get(Call, DATA_CALL).publication_state = "draft"
    db.commit()
    assert [c["id"] for c in client.get(CALLS_URL, headers=everything).json()] == [IA_CALL]


def test_coordination_registers_but_still_cannot_read_dossiers(client):
    headers = login(client, COORD)
    receipt = client.post(URL, headers=headers, json=manual()).json()
    assert client.get(f"/api/v1/applications/{receipt['id']}", headers=headers).status_code == 403
    assert client.get("/api/v1/applications", headers=headers).status_code == 403


def test_the_dossier_history_and_audit_show_channel_and_author(client, db):
    receipt = client.post(URL, headers=login(client, SEL_IA), json=manual(origin_channel="derivacion")).json()
    detail = client.get(f"/api/v1/applications/{receipt['id']}", headers=login(client, CAPT_IA)).json()
    assert detail["origin_channel"] == "derivacion" and detail["registered_by"]
    [event] = detail["events"]
    assert event["tipo"] == "creada" and event["actor"] == detail["registered_by"]
    assert event["resumen"] == "Alta registrada por el equipo. Canal de origen: derivación"
    audited = db.scalar(select(AuditEvent).where(AuditEvent.action == "application.created", AuditEvent.target_id == receipt["id"]))
    assert audited.meta["origin_channel"] == "derivacion" and audited.actor_user_id == user_id(db, SEL_IA)
    assert EMAIL not in str(audited.meta) and "Sintética" not in str(audited.meta)


def test_public_applications_are_marked_as_form(client, db):
    receipt = client.post("/api/v1/applications", json=new_application()).json()
    application = stored(db, receipt)
    assert application.origin_channel == "formulario" and application.created_by is None
    detail = client.get(f"/api/v1/applications/{receipt['id']}", headers=login(client, ADMIN)).json()
    assert detail["origin_channel"] == "formulario" and detail["registered_by"] is None


def test_the_public_form_cannot_choose_a_channel_or_an_author(client, db):
    forged = new_application(origin_channel="telefono", created_by=str(user_id(db, ADMIN)))
    application = stored(db, client.post("/api/v1/applications", json=forged).json())
    assert application.origin_channel == "formulario" and application.created_by is None


@pytest.mark.parametrize(
    "over",
    [
        {"origin_channel": "formulario"},
        {"origin_channel": "fax"},
        {"origin_channel": None},
        {"confirma_datos_sinteticos": False},
        {"confirma_datos_sinteticos": 1},
        {"confirma_datos_sinteticos": "true"},
        {"email": "no-es-un-correo"},
        {"nombre": " a "},
        {"motivacion": "corta"},
        {"disponibilidad": "Noche"},
        {"call_id": "   "},
    ],
)
def test_manual_intake_applies_the_same_validations(client, db, over):
    before = applications(db)
    assert client.post(URL, headers=login(client, SEL_IA), json=manual(**over)).status_code == 422
    assert applications(db) == before


@pytest.mark.parametrize("missing", ["origin_channel", "confirma_datos_sinteticos"])
def test_channel_and_confirmation_are_required(client, missing):
    body = manual()
    del body[missing]
    assert client.post(URL, headers=login(client, SEL_IA), json=body).status_code == 422


def test_closed_draft_and_unknown_calls_behave_as_on_the_public_form(client, db):
    headers = login(client, ADMIN)
    assert client.post(URL, headers=headers, json=manual(call_id=CLOSED_CALL)).status_code == 409
    assert client.post(URL, headers=headers, json=manual(call_id="NO-EXISTE")).status_code == 404
    db.get(Call, DATA_CALL).publication_state = "draft"
    db.commit()
    before = applications(db)
    assert client.post("/api/v1/applications", json=new_application(call_id=DATA_CALL)).status_code == 404
    assert client.post(URL, headers=headers, json=manual(call_id=DATA_CALL)).status_code == 404
    assert applications(db) == before


def test_an_unpublished_call_outside_scope_looks_like_an_unknown_one(client, db):
    db.get(Call, DATA_CALL).publication_state = "draft"
    db.commit()
    headers = login(client, SEL_IA)
    draft = client.post(URL, headers=headers, json=manual(call_id=DATA_CALL))
    unknown = client.post(URL, headers=headers, json=manual(call_id="NO-EXISTE"))
    assert draft.status_code == unknown.status_code == 404
    assert draft.json()["code"] == unknown.json()["code"] and draft.json().get("message") == unknown.json().get("message")


def test_a_programme_assignment_covers_its_calls_and_no_others(client, db):
    assignment = db.scalar(select(RoleAssignment).where(RoleAssignment.user_id == user_id(db, SEL_IA)))
    assignment.scope_type, assignment.scope_id = "program", "P-IA"
    db.commit()
    headers = login(client, SEL_IA)
    assert [c["id"] for c in client.get(CALLS_URL, headers=headers).json()] == [IA_CALL]
    assert client.post(URL, headers=headers, json=manual()).status_code == 201
    assert client.post(URL, headers=headers, json=manual(call_id=DATA_CALL)).status_code == 403


@pytest.mark.parametrize("origin", MANUAL_ORIGINS)
def test_every_manual_channel_is_stored_and_written_in_the_history(client, db, origin):
    receipt = client.post(URL, headers=login(client, SEL_IA), json=manual(origin_channel=origin))
    assert receipt.status_code == 201, receipt.text
    assert stored(db, receipt.json()).origin_channel == origin
    event = db.scalar(select(ApplicationEvent).where(ApplicationEvent.application_id == receipt.json()["id"]))
    assert "Canal de origen: " in event.resumen


def test_a_public_application_sent_with_a_session_keeps_its_author(client, db):
    headers = login(client, ASPIRANTE)
    receipt = client.post("/api/v1/applications", headers=headers, json=new_application(email=ASPIRANTE)).json()
    application = stored(db, receipt)
    assert application.origin_channel == "formulario" and application.created_by == user_id(db, ASPIRANTE)


def test_the_migration_recovers_known_authors_from_the_creation_event(client, db):
    signed = client.post("/api/v1/applications", headers=login(client, ASPIRANTE), json=new_application(email=ASPIRANTE)).json()
    anonymous = client.post("/api/v1/applications", json=new_application()).json()
    author = user_id(db, ASPIRANTE)
    db.close()
    config = Config(os.path.join(API_DIR, "alembic.ini"))
    config.set_main_option("script_location", os.path.join(API_DIR, "alembic"))
    command.downgrade(config, "0021")
    command.upgrade(config, "head")
    assert stored(db, signed).created_by == author
    assert stored(db, anonymous).created_by is None


def test_the_same_duplicate_control_applies_across_both_intakes(client, db):
    headers = login(client, SEL_IA)
    assert client.post("/api/v1/applications", json=new_application()).status_code == 201
    assert client.post(URL, headers=headers, json=manual(email=f" {EMAIL.upper()} ")).status_code == 409

    admin = login(client, ADMIN)
    receipt = client.post(URL, headers=admin, json=manual(call_id=DATA_CALL)).json()
    assert db.scalar(select(func.count()).select_from(Person).where(Person.email == EMAIL)) == 2
    review = db.scalar(select(IdentityReview).where(IdentityReview.application_id == receipt["id"]))
    assert review.decision is None
    assert client.post("/api/v1/applications", json=new_application(call_id=DATA_CALL)).status_code == 409


def test_registering_never_joins_the_record_of_the_account_that_registers(client, db):
    """A staff account that is also a person record must not receive the applications it types in."""
    person = Person(display_name="Personal Sintético", email=EMAIL, is_synthetic=True)
    db.add(person)
    db.flush()
    db.get(User, user_id(db, ADMIN)).person_id = person.id
    db.commit()
    receipt = client.post(URL, headers=login(client, ADMIN), json=manual()).json()
    assert stored(db, receipt).person_id != person.id
    assert db.scalar(select(func.count()).select_from(IdentityReview)) == 1
    assert db.scalar(select(func.count()).select_from(ApplicationEvent).where(ApplicationEvent.application_id == receipt["id"])) == 1


def test_a_call_loaded_before_the_lock_is_read_again(db):
    """The manual route looks the call up to authorise it. Another intake may commit before this one locks the row."""
    loaded = db.get(Call, IA_CALL)
    stale_sequence = loaded.next_seq
    with SessionLocal() as other:
        other.get(Call, IA_CALL).next_seq = stale_sequence + 5
        other.commit()
    application = create_application(db, ApplicationCreate(**new_application()), None)
    assert application.codigo == f"{loaded.codigo_prefix}-{stale_sequence + 5:04d}"


def test_a_call_closed_between_the_check_and_the_lock_accepts_nothing(db):
    db.get(Call, IA_CALL)
    with SessionLocal() as other:
        other.get(Call, IA_CALL).estado = "cerrada"
        other.commit()
    with pytest.raises(HTTPException) as refused:
        create_application(db, ApplicationCreate(**new_application()), None)
    assert refused.value.status_code == 409


def test_parallel_manual_and_public_intakes_get_different_codes(client, db):
    headers = login(client, ADMIN)
    gate = threading.Barrier(6)

    def submit(number):
        with TestClient(app) as other:
            gate.wait(timeout=8)
            email = f"paralela.{number}@example.test"
            if number % 2:
                return other.post(URL, headers=headers, json=manual(email=email))
            return other.post("/api/v1/applications", json=new_application(email=email))

    with ThreadPoolExecutor(max_workers=6) as pool:
        responses = list(pool.map(submit, range(6)))
    assert [r.status_code for r in responses] == [201] * 6
    assert len({r.json()["codigo"] for r in responses}) == 6


@pytest.mark.parametrize(
    "channel, with_author, constraint",
    [("telefono", False, "ck_application_manual_author"), ("fax", True, "ck_application_origin_channel")],
)
def test_the_database_requires_a_known_channel_and_an_author_for_manual_ones(client, db, channel, with_author, constraint):
    application = stored(db, client.post("/api/v1/applications", json=new_application()).json())
    application.origin_channel = channel
    application.created_by = user_id(db, ADMIN) if with_author else None
    with pytest.raises(IntegrityError) as refused:
        db.commit()
    assert refused.value.orig.diag.constraint_name == constraint
