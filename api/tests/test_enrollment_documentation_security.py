from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.main import app
from app.modules.audit.models import AuditEvent
from app.modules.identity.models import User
from app.modules.learning import documentation_service as service
from tests.conftest import ADMIN, CODER, login
from tests.test_enrollment_documentation_accreditation import admitted_enrollment
from tests.test_enrollment_documentation_reads import own_enrollment, path


@pytest.mark.parametrize('operation', ['accredit', 'revoke'])
def test_concurrent_changes_accept_only_one_expected_version(client, db, operation):
    row = admitted_enrollment(client, db)
    admin = login(client, ADMIN)
    version = 1
    if operation == 'revoke':
        assert client.post(path(row.id) + '/accredit', headers=admin, json={'expected_version': 1}).status_code == 200
        version = 2
    ready = Barrier(2)

    def mutate():
        with TestClient(app) as caller:
            ready.wait(timeout=10)
            return caller.post(path(row.id) + '/' + operation, headers=admin, json={'expected_version': version}).status_code

    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(lambda _: mutate(), range(2)))
    assert sorted(results) == [200, 409]
    db.refresh(row)
    assert row.documentation_version == version + 1
    action = 'enrollment.documentation_' + ('accredited' if operation == 'accredit' else 'revoked')
    assert db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action == action)) == 1


@pytest.mark.parametrize('operation', ['accredit', 'revoke'])
def test_audit_failure_after_flush_rolls_back_documentary_change(client, db, monkeypatch, operation):
    row = admitted_enrollment(client, db)
    admin = login(client, ADMIN)
    if operation == 'revoke':
        assert client.post(path(row.id) + '/accredit', headers=admin, json={'expected_version': 1}).status_code == 200
    db.refresh(row)
    before = (row.documentation_state, row.documentation_version, row.documentation_accredited_by, row.documentation_accredited_at)
    action = 'enrollment.documentation_' + ('accredited' if operation == 'accredit' else 'revoked')
    original = service.audit.record

    def fail_documentation(session, actor, current_action, *args, **kwargs):
        if current_action == action:
            session.flush()
            raise RuntimeError('Synthetic documentation audit failure')
        return original(session, actor, current_action, *args, **kwargs)

    monkeypatch.setattr(service.audit, 'record', fail_documentation)
    with TestClient(app, raise_server_exceptions=False) as failing:
        response = failing.post(path(row.id) + '/' + operation, headers=admin, json={'expected_version': before[1]})
    assert response.status_code == 500
    db.refresh(row)
    assert (row.documentation_state, row.documentation_version, row.documentation_accredited_by, row.documentation_accredited_at) == before
    assert db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action == action)) == 0


@pytest.mark.parametrize('invalid', ['missing_actor', 'pending_actor', 'zero_version'])
def test_database_rejects_inconsistent_documentation_evidence(db, invalid):
    row = own_enrollment(db)
    admin_id = db.scalar(select(User.id).where(User.email == ADMIN))
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            if invalid == 'missing_actor':
                row.documentation_state = 'accredited'
            elif invalid == 'pending_actor':
                row.documentation_accredited_by = admin_id
            else:
                row.documentation_version = 0
            db.flush()


def test_owner_cannot_self_accredit_and_inactive_admission_cannot_be_accredited(client, db):
    legacy = own_enrollment(db)
    assert client.post(path(legacy.id) + '/accredit', headers=login(client, CODER), json={'expected_version': 1}).status_code == 403
    row = admitted_enrollment(client, db)
    row.estado = 'baja_voluntaria'
    db.commit()
    response = client.post(path(row.id) + '/accredit', headers=login(client, ADMIN), json={'expected_version': 1})
    assert response.status_code == 409 and response.json()['code'] == 'documentation_admission_required'
    db.refresh(row)
    assert row.documentation_state == 'pending' and row.estado == 'baja_voluntaria'
