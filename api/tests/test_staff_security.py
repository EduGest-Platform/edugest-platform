"""PostgreSQL regressions for invitation invalidation and review boundaries."""
import uuid
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.db import utcnow
from app.main import app
from app.modules.staff import service
from app.modules.staff.models import AccessChangeRequest, Invitation, StaffProfile
from tests.conftest import ADMIN, SEL_IA, login
from tests.test_staff_access_review import active_profile, request
from tests.test_staff_issuance import issue


@pytest.mark.parametrize('condition', ['expired', 'revoked', 'rotated', 'inactive'])
def test_unavailable_invitation_never_activates_profile(client, db, condition):
    admin = login(client, ADMIN)
    receipt = issue(client, db, admin).json()
    row = db.get(Invitation, uuid.UUID(receipt['invitation']['id']))
    profile = db.get(StaffProfile, row.staff_profile_id)
    if condition == 'expired':
        row.created_at = utcnow() - timedelta(hours=2)
        row.expires_at = utcnow() - timedelta(hours=1)
        db.commit()
    elif condition == 'inactive':
        profile.state = 'inactive'
        db.commit()
    else:
        operation = 'revoke' if condition == 'revoked' else 'renew'
        response = client.post(f'/api/v1/staff/invitations/{row.id}/{operation}', headers=admin, json={})
        assert response.status_code in (200, 201)
    response = client.post('/api/v1/staff/invitations/accept', headers=login(client, SEL_IA), json={'token': receipt['token']})
    assert response.status_code == 400
    assert response.json()['code'] == 'invitation_unavailable'
    db.refresh(row)
    db.refresh(profile)
    assert row.used_at is None
    assert profile.state == ('inactive' if condition == 'inactive' else 'pending')


def test_failed_acceptance_audit_rolls_back_activation(client, db, monkeypatch):
    receipt = issue(client, db, login(client, ADMIN)).json()
    owner = login(client, SEL_IA)
    original = service.audit.record

    def fail_acceptance(session, actor, action, *args, **kwargs):
        if action == 'staff.invitation_accepted':
            session.flush()
            raise RuntimeError('Synthetic audit failure')
        return original(session, actor, action, *args, **kwargs)

    monkeypatch.setattr(service.audit, 'record', fail_acceptance)
    with TestClient(app, raise_server_exceptions=False) as failing_client:
        response = failing_client.post('/api/v1/staff/invitations/accept', headers=owner, json={'token': receipt['token']})
    assert response.status_code == 500
    row = db.get(Invitation, uuid.UUID(receipt['invitation']['id']))
    assert row.used_at is None
    assert db.get(StaffProfile, row.staff_profile_id).state == 'pending'


def test_non_admin_cannot_review_and_review_cannot_be_repeated(client, db):
    owner = active_profile(client, db, SEL_IA)
    row = request(client, owner)
    path = '/api/v1/staff/access-requests/' + row['id'] + '/review'
    assert client.post(path, headers=owner, json={'approved': True}).status_code == 403
    admin = login(client, ADMIN)
    assert client.post(path, headers=admin, json={'approved': False}).status_code == 200
    assert client.post(path, headers=admin, json={'approved': True}).status_code == 409
    stored = db.get(AccessChangeRequest, uuid.UUID(row['id']))
    assert stored.state == 'rejected' and stored.applied_assignment_id is None


def test_unknown_scope_is_checked_at_review_without_consuming_request(client, db):
    owner = active_profile(client, db, SEL_IA)
    response = client.post('/api/v1/staff/access-requests', headers=owner, json={
        'requested_role': 'docente', 'scope_type': 'cohort', 'scope_id': 'NONEXISTENT'})
    assert response.status_code == 201
    identity = response.json()['id']
    reviewed = client.post('/api/v1/staff/access-requests/' + identity + '/review', headers=login(client, ADMIN), json={'approved': True})
    assert reviewed.status_code == 422
    row = db.get(AccessChangeRequest, uuid.UUID(identity))
    assert row.state == 'requested' and row.reviewed_by is None
