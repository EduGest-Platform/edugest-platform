"""KAN-128: browser preflight must permit authenticated requirement-review PUTs."""

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


def test_requirement_put_preflight_accepts_configured_origin():
    with TestClient(app) as client:
        response = client.options(
            "/api/v1/applications/00000000-0000-0000-0000-000000000001/requirement-reviews/demo",
            headers={
                "Origin": settings.cors_origins[0],
                "Access-Control-Request-Method": "PUT",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == settings.cors_origins[0]
    assert "PUT" in response.headers["access-control-allow-methods"].split(", ")
    allowed = response.headers["access-control-allow-headers"].lower()
    assert "authorization" in allowed and "content-type" in allowed


def test_requirement_put_preflight_rejects_unknown_origin():
    with TestClient(app) as client:
        response = client.options(
            "/api/v1/applications/00000000-0000-0000-0000-000000000001/requirement-reviews/demo",
            headers={"Origin": "https://untrusted.example.test", "Access-Control-Request-Method": "PUT"},
        )
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers
