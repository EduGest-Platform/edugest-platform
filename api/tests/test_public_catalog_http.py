import pytest
from fastapi.testclient import TestClient

from app.core.db import get_db
from app.main import app


class EmptyCatalog:
    def scalar(self, query):
        return 0

    def execute(self, query):
        return []


@pytest.fixture
def public_client():
    def empty_database():
        yield EmptyCatalog()

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = empty_database
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)


def test_public_catalog_is_anonymous_and_does_not_trust_authorization_header(public_client):
    for headers in ({}, {'Authorization': 'Bearer synthetic-invalid'}):
        response = public_client.get('/api/v1/public/courses', headers=headers)
        assert response.status_code == 200
        assert response.json() == {'items': [], 'total': 0}
        assert response.headers['cache-control'] == 'no-store'


@pytest.mark.parametrize('query', ['limit=0', 'limit=101', 'offset=-1', 'admission_state=draft', 'program_id='])
def test_public_pagination_and_filters_are_validated(public_client, query):
    assert public_client.get('/api/v1/public/courses?' + query).status_code == 422


def test_public_routes_have_no_bearer_requirement_but_admin_routes_do():
    schema = app.openapi()['paths']
    assert not schema['/api/v1/public/courses']['get'].get('security')
    assert not schema['/api/v1/public/courses/{course_id}']['get'].get('security')
    assert schema['/api/v1/catalog/publications']['get']['security']
