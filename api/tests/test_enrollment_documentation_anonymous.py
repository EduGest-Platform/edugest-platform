from fastapi.testclient import TestClient

from app.main import app

PATH = '/api/v1/enrollments/00000000-0000-0000-0000-000000000000/documentation'


def test_documentation_is_not_public():
    with TestClient(app) as client:
        assert client.get(PATH).status_code == 401
        assert client.post(PATH + '/accredit', json={'expected_version': 1}).status_code == 401
        assert client.post(PATH + '/revoke', json={'expected_version': 1}).status_code == 401
        assert client.get(PATH + '/history').status_code == 401
