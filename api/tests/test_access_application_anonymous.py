from fastapi.testclient import TestClient

from app.main import app

PATH = '/api/v1/staff/access-requests/00000000-0000-0000-0000-000000000000'


def test_access_application_requires_authentication():
    with TestClient(app) as client:
        assert client.get(PATH + '/application-preview').status_code == 401
        assert client.post(PATH + '/apply', json={'confirm': True, 'requested_role': 'docente', 'scope_type': 'cohort', 'scope_id': 'COH-IA'}).status_code == 401
