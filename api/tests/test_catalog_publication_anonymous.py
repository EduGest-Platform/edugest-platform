import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.parametrize('method,path,body', [
    ('GET', '/api/v1/catalog/publications', None),
    ('GET', '/api/v1/calls/CONV-IA-2027A/publication', None),
    ('PUT', '/api/v1/calls/CONV-IA-2027A/publication', {'state': 'draft', 'expected_version': 1}),
])
def test_anonymous_cannot_manage_publication(method, path, body):
    with TestClient(app) as client:
        response = client.request(method, path, json=body)
    assert response.status_code == 401
