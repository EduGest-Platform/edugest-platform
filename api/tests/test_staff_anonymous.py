import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.parametrize(('path', 'body'), [
    ('/api/v1/staff/invitations', {'user_id': str(uuid.uuid4())}),
    (f'/api/v1/staff/invitations/{uuid.uuid4()}/renew', {}),
    (f'/api/v1/staff/invitations/{uuid.uuid4()}/revoke', None),
])
def test_staff_management_rejects_anonymous_requests_before_db_access(path, body):
    with TestClient(app) as client:
        response = client.post(path, json=body)
    assert response.status_code == 401
