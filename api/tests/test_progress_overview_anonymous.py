from fastapi.testclient import TestClient

from app.main import app


def test_overview_is_not_public():
    with TestClient(app) as client:
        assert client.get('/api/v1/cohorts/COH-IA/progress-overview').status_code == 401
