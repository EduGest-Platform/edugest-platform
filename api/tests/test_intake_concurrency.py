from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.modules.admissions.models import Application, ApplicationEvent
from app.modules.audit.models import AuditEvent
from app.modules.catalog.models import Call
from app.modules.identity.models import Person
from tests.conftest import new_application

IA_CALL = "CONV-IA-2027A"
DATA_CALL = "CONV-DATA-2027A"
EMAIL = "intake.concurrent@example.test"


def submit_in_parallel(payloads):
    gate = Barrier(len(payloads))

    def submit(body):
        with TestClient(app) as client:
            gate.wait(timeout=8)
            return client.post("/api/v1/applications", json=body)

    with ThreadPoolExecutor(max_workers=len(payloads)) as pool:
        return list(pool.map(submit, payloads))


def assert_created_once_per_call(db, calls, responses):
    db.expire_all()
    person = db.scalars(select(Person).where(Person.email == EMAIL)).one()
    applications = db.scalars(select(Application).where(Application.person_id == person.id)).all()
    assert sorted(row.call_id for row in applications) == sorted(calls)
    created_ids = {response.json()["id"] for response in responses if response.status_code == 201}
    assert created_ids == {str(row.id) for row in applications}
    for row in applications:
        event = db.scalars(select(ApplicationEvent).where(ApplicationEvent.application_id == row.id)).one()
        assert event.tipo == "creada" and event.actor_user_id is None
        audit = db.scalars(select(AuditEvent).where(
            AuditEvent.target_id == str(row.id), AuditEvent.action == "application.created",
        )).one()
        assert audit.meta["call_id"] == row.call_id
    return applications


def test_simultaneous_double_submission_consumes_one_sequence_and_writes_once(db):
    sequence = db.get(Call, IA_CALL).next_seq
    prefix = db.get(Call, IA_CALL).codigo_prefix
    responses = submit_in_parallel([
        new_application(call_id=IA_CALL, email=EMAIL),
        new_application(call_id=IA_CALL, email=f"  {EMAIL.upper()}  "),
    ])
    assert sorted(response.status_code for response in responses) == [201, 409]
    application, = assert_created_once_per_call(db, [IA_CALL], responses)
    assert application.codigo == f"{prefix}-{sequence:04d}"
    assert db.get(Call, IA_CALL).next_seq == sequence + 1


def test_simultaneous_applications_in_two_calls_share_only_the_person(db):
    baseline = {call_id: db.get(Call, call_id).next_seq for call_id in (IA_CALL, DATA_CALL)}
    responses = submit_in_parallel([
        new_application(call_id=IA_CALL, email=EMAIL),
        new_application(call_id=DATA_CALL, email=EMAIL.upper()),
    ])
    assert [response.status_code for response in responses] == [201, 201]
    applications = assert_created_once_per_call(db, [IA_CALL, DATA_CALL], responses)
    assert len({row.codigo for row in applications}) == 2
    for call_id, sequence in baseline.items():
        assert db.get(Call, call_id).next_seq == sequence + 1
