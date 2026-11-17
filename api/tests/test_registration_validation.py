"""KAN-124: F1 registration boundaries and transactional rejection guarantees."""

import uuid

import pytest
from sqlalchemy import func, select

from app.modules.admissions.models import Application, ApplicationEvent
from app.modules.audit.models import AuditEvent
from app.modules.catalog.models import Call
from app.modules.identity.models import Person
from tests.conftest import new_application


def snapshot(db):
    db.expire_all()
    counts = tuple(db.scalar(select(func.count()).select_from(model)) for model in (Person, Application, ApplicationEvent, AuditEvent))
    counters = dict(db.execute(select(Call.id, Call.next_seq)).all())
    return counts, counters


@pytest.mark.parametrize(
    "field,value",
    [
        ("nombre", "A"),
        ("nombre", "N" * 121),
        ("motivacion", "M" * 9),
        ("motivacion", "M" * 2001),
        ("email", "a" * 65 + "@example.test"),
        ("email", "two@@example.test"),
        ("email", "two words@example.test"),
        ("call_id", "C" * 31),
        ("disponibilidad", "Nocturna"),
        ("acepta_datos_sinteticos", None),
    ],
)
def test_invalid_fields_have_no_persistence_or_counter_side_effects(client, db, field, value):
    before = snapshot(db)
    response = client.post("/api/v1/applications", json=new_application(**{field: value}))
    assert response.status_code == 422
    assert any(item["loc"][-1] == field for item in response.json()["detail"])
    assert snapshot(db) == before


@pytest.mark.parametrize("field", ["call_id", "nombre", "email", "motivacion", "disponibilidad", "acepta_datos_sinteticos"])
def test_missing_required_fields_are_rejected_without_partial_records(client, db, field):
    payload = new_application()
    del payload[field]
    before = snapshot(db)
    response = client.post("/api/v1/applications", json=payload)
    assert response.status_code == 422
    assert any(item["loc"][-1] == field for item in response.json()["detail"])
    assert snapshot(db) == before


@pytest.mark.parametrize("name_size,motivation_size", [(2, 10), (120, 2000)])
def test_exact_text_boundaries_are_accepted_and_persisted(client, db, name_size, motivation_size):
    response = client.post("/api/v1/applications", json=new_application(nombre="N" * name_size, motivacion="M" * motivation_size))
    assert response.status_code == 201
    application = db.get(Application, uuid.UUID(response.json()["id"]))
    person = db.get(Person, application.person_id)
    assert len(person.display_name) == name_size
    assert len(application.motivacion) == motivation_size


@pytest.mark.parametrize("availability", ["Mañana", "Tarde", "Flexible"])
def test_supported_availability_values_round_trip(client, db, availability):
    response = client.post("/api/v1/applications", json=new_application(disponibilidad=availability))
    assert response.status_code == 201
    application = db.get(Application, uuid.UUID(response.json()["id"]))
    assert application.disponibilidad == availability


@pytest.mark.parametrize("call_id,status", [("CONV-IA-2026B", 409), ("NO-EXISTE", 404)])
def test_rejected_call_does_not_create_person_events_or_consume_codes(client, db, call_id, status):
    before = snapshot(db)
    response = client.post("/api/v1/applications", json=new_application(call_id=call_id))
    assert response.status_code == status
    assert snapshot(db) == before


def test_rejected_duplicate_preserves_every_record_counter_and_original_identity(client, db):
    original = client.post("/api/v1/applications", json=new_application(nombre="Nombre Sintético Original"))
    assert original.status_code == 201
    before = snapshot(db)
    duplicate = client.post("/api/v1/applications", json=new_application(email="  NUEVA.PERSONA@EXAMPLE.TEST  ", nombre="Nombre Sustituto"))
    assert duplicate.status_code == 409
    assert snapshot(db) == before
    person = db.scalar(select(Person).where(Person.email == "nueva.persona@example.test"))
    assert person.display_name == "Nombre Sintético Original"


def test_public_registration_cannot_choose_stage_identity_or_event_author(client, db):
    response = client.post("/api/v1/applications", json=new_application(
        stage="admitida", role="admin", person_id=str(uuid.uuid4()), actor_user_id=str(uuid.uuid4()),
    ))
    # Extra fields are ignored by the current contract; they must never gain authority.
    assert response.status_code == 201
    assert response.json()["stage"] == "enviada"
    application = db.get(Application, uuid.UUID(response.json()["id"]))
    assert application.stage == "enviada"
    event = db.scalar(select(ApplicationEvent).where(ApplicationEvent.application_id == application.id))
    assert event.tipo == "creada"
    assert event.actor_user_id is None
    person = db.get(Person, application.person_id)
    assert person.email == "nueva.persona@example.test"
    assert person.is_synthetic
