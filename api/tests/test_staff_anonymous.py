import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.parametrize(('path', 'body'), [
    ('/api/v1/staff/invitations', {'user_id': str(uuid.uuid4())}),
    (f'/api/v1/staff/invitations/{uuid.uuid4()}/renew', {}),
    (f'/api/v1/staff/invitations/{uuid.uuid4()}/revoke', None),
    ('/api/v1/staff/invitations/accept', {'token': 'synthetic-token-' + 'x' * 32}),
    ('/api/v1/staff/access-requests', {'requested_role': 'docente', 'scope_type': 'cohort', 'scope_id': 'COH-IA'}),
    (f'/api/v1/staff/access-requests/{uuid.uuid4()}/review', {'approved': True}),
])
def test_staff_management_rejects_anonymous_requests_before_db_access(path, body):
    with TestClient(app) as client:
        response = client.post(path, json=body)
    assert response.status_code == 401


def test_own_staff_profile_is_not_public():
    with TestClient(app) as client:
        assert client.get('/api/v1/staff/me').status_code == 401
        assert client.get('/api/v1/staff/access-requests').status_code == 401
