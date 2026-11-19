"""CORS must allow every HTTP method the API declares, or the browser blocks the call before it reaches FastAPI."""

import pytest

from app.core.config import settings
from app.main import app
from tests.conftest import ADMIN, login

ALLOWED_ORIGIN = settings.cors_origins[0]
FOREIGN_ORIGIN = "https://attacker.example"
HTTP_METHODS = {"get", "put", "post", "delete", "patch"}
# Read from the OpenAPI schema: it lists every operation whatever FastAPI does internally with routers.
DECLARED_METHODS = sorted({m.upper() for path in app.openapi()["paths"].values() for m in path if m in HTTP_METHODS})


def preflight(client, method, origin=ALLOWED_ORIGIN, path="/api/v1/applications"):
    return client.options(
        path,
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": method,
            "Access-Control-Request-Headers": "authorization,content-type",
        },
    )


def test_the_api_declares_the_methods_this_file_protects():
    assert {"GET", "POST", "PUT"} <= set(DECLARED_METHODS)


@pytest.mark.parametrize("method", DECLARED_METHODS)
def test_every_declared_method_passes_the_preflight_from_an_allowed_origin(client, method):
    r = preflight(client, method)
    assert r.status_code == 200, r.text
    assert method in r.headers["access-control-allow-methods"]
    assert r.headers["access-control-allow-origin"] == ALLOWED_ORIGIN


def test_put_preflight_for_requirement_reviews_is_accepted(client):
    r = preflight(client, "PUT", path="/api/v1/applications/any/requirement-reviews/identity-document")
    assert r.status_code == 200
    assert "PUT" in r.headers["access-control-allow-methods"]


def test_foreign_origin_is_still_rejected_for_put(client):
    r = preflight(client, "PUT", origin=FOREIGN_ORIGIN)
    assert r.status_code == 400
    assert "access-control-allow-origin" not in r.headers


def test_real_put_from_an_allowed_origin_is_readable_by_the_browser(client):
    headers = login(client, ADMIN)
    application = client.get("/api/v1/applications", headers=headers).json()["items"][0]
    configured = client.post(f"/api/v1/calls/{application['call_id']}/requirements", headers=headers,
                             json={"ref": "identity-document", "code": "identity-document", "label": "Synthetic test", "kind": "required"})
    assert configured.status_code == 201, configured.text
    url = f"/api/v1/applications/{application['id']}/requirement-reviews/identity-document"
    r = client.put(url, json={"result": "met", "reason": "Documento comprobado"}, headers={**headers, "Origin": ALLOWED_ORIGIN})
    assert r.status_code == 201, r.text
    assert r.headers["access-control-allow-origin"] == ALLOWED_ORIGIN
