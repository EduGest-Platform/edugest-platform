from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.main import app
from app.modules.audit.models import AuditEvent
from app.modules.catalog import publication_service as service
from app.modules.catalog.models import Call
from tests.conftest import ADMIN, login

CALL = 'CONV-IA-2027A'
PATH = '/api/v1/calls/' + CALL + '/publication'


def publication_events(db):
    return db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action == 'catalog.publication_changed'))


def test_repeated_current_state_does_not_create_a_new_version_or_audit(client, db):
    admin = login(client, ADMIN)
    original = client.get(PATH, headers=admin).json()
    before = publication_events(db)
    response = client.put(PATH, headers=admin, json={'state': original['state'], 'expected_version': original['version']})
    assert response.status_code == 200 and response.json() == original
    assert publication_events(db) == before


def test_audit_failure_after_flush_rolls_back_state_and_version(client, db, monkeypatch):
    admin = login(client, ADMIN)
    original = client.get(PATH, headers=admin).json()
    audit_record = service.audit.record

    def fail_publication(session, actor, action, *args, **kwargs):
        if action == 'catalog.publication_changed':
            session.flush()
            raise RuntimeError('Synthetic publication audit failure')
        return audit_record(session, actor, action, *args, **kwargs)

    monkeypatch.setattr(service.audit, 'record', fail_publication)
    with TestClient(app, raise_server_exceptions=False) as failing_client:
        response = failing_client.put(PATH, headers=admin, json={'state': 'draft', 'expected_version': original['version']})
    assert response.status_code == 500
    row = db.get(Call, CALL)
    assert row.publication_state == original['state'] and row.publication_version == original['version']
    assert publication_events(db) == 0


def test_simultaneous_publication_changes_accept_exactly_one_version(client, db):
    admin = login(client, ADMIN)
    version = client.get(PATH, headers=admin).json()['version']
    ready = Barrier(2)

    def withdraw():
        with TestClient(app) as caller:
            ready.wait(timeout=10)
            return caller.put(PATH, headers=admin, json={'state': 'draft', 'expected_version': version}).status_code

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(lambda _: withdraw(), range(2)))
    assert sorted(results) == [200, 409]
    assert publication_events(db) == 1
    assert db.get(Call, CALL).publication_version == version + 1


def test_incomplete_offer_cannot_change_visibility(client, db):
    row = db.get(Call, CALL)
    row.publication_state, row.nombre = 'draft', '   '
    db.commit()
    response = client.put(PATH, headers=login(client, ADMIN), json={'state': 'published', 'expected_version': row.publication_version})
    assert response.status_code == 422 and response.json()['code'] == 'public_offer_incomplete'
    db.refresh(row)
    assert row.publication_state == 'draft' and publication_events(db) == 0


def test_new_call_defaults_to_draft_and_database_rejects_unknown_state(db):
    row = Call(id='SYNTHETIC-DRAFT', program_id='P-IA', nombre='Synthetic draft', codigo_prefix='SYNTH',
               opens_on=date(2030, 1, 1), closes_on=date(2030, 2, 1), plazas=10, estado='abierta')
    db.add(row)
    db.flush()
    assert row.publication_state == 'draft' and row.publication_version == 1
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            row.publication_state = 'unknown'
            db.flush()
