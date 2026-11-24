"""Actual discussion HTTP routing rejects anonymous requests before database access."""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.mark.parametrize(('method', 'path', 'body'), [
    ('post', '/api/v1/discussion-threads', {'scope_type': 'program', 'program_id': 'P-IA', 'subject': 'Synthetic topic'}),
    ('get', '/api/v1/discussion-threads?scope_type=program&program_id=P-IA', None),
    ('get', f'/api/v1/discussion-threads/{uuid.uuid4()}', None),
])
def test_thread_routes_require_authentication(method, path, body):
    with TestClient(app) as client:
        response = client.request(method, path, json=body)
    assert response.status_code == 401
    assert response.headers['www-authenticate'].lower() == 'bearer'
