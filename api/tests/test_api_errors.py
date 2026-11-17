"""KAN-105: uniform errors, server-side request IDs, no data leakage in bodies or logs."""

import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy import select

from app.core.error_handling import INTERNAL_ERROR_DETAIL, REQUEST_ID_HEADER, install_error_handling
from app.modules.audit.models import AuditEvent
from tests.conftest import ADMIN, CAPT_IA, login, new_application

SENSITIVE = "dato.sensible.no.debe.salir@example.test"


def assert_correlated(response) -> str:
    """The header and the body must carry the same server-generated ID."""
    header = response.headers[REQUEST_ID_HEADER]
    assert header and response.json()["request_id"] == header
    return header


def test_401_keeps_detail_and_adds_request_id(client):
    r = client.get("/api/v1/applications")
    assert r.status_code == 401
    assert r.json()["detail"] == "Sesión no válida o caducada"
    assert r.headers["www-authenticate"] == "Bearer"
    assert_correlated(r)


def test_403_keeps_detail_and_adds_request_id(client):
    ia_headers = login(client, CAPT_IA)
    other = login(client, ADMIN)
    data_app = next(a for a in client.get("/api/v1/applications", headers=other, params={"limit": 200}).json()["items"] if a["program_id"] == "P-DATA")
    r = client.get(f"/api/v1/applications/{data_app['id']}", headers=ia_headers)
    assert r.status_code == 403
    assert r.json()["detail"] == "No tienes permiso sobre este ámbito"
    assert_correlated(r)


def test_409_duplicate_application_is_correlated_and_audits_nothing_extra(client, db):
    body = new_application(email=SENSITIVE)
    assert client.post("/api/v1/applications", json=body).status_code == 201
    audits_before = len(list(db.scalars(select(AuditEvent))))
    r = client.post("/api/v1/applications", json=body)
    assert r.status_code == 409
    assert r.json()["detail"] == "Ya existe una candidatura con este correo en esta convocatoria"
    assert_correlated(r)
    db.expire_all()
    assert len(list(db.scalars(select(AuditEvent)))) == audits_before
    assert all(SENSITIVE not in str(e.meta) and SENSITIVE not in (e.target_id or "") for e in db.scalars(select(AuditEvent)))


def test_422_lists_fields_without_echoing_user_input(client):
    r = client.post("/api/v1/applications", json=new_application(email=SENSITIVE, motivacion="corta"))
    assert r.status_code == 422
    detail = r.json()["detail"]
    assert detail and all(set(e) == {"loc", "msg", "type"} for e in detail)
    assert "motivacion" in {part for e in detail for part in e["loc"]}
    assert SENSITIVE not in r.text and "corta" not in r.text
    assert_correlated(r)


def test_404_unknown_route_is_uniform(client):
    r = client.get("/api/v1/no-existe")
    assert r.status_code == 404 and r.json()["detail"] == "Not Found"
    assert_correlated(r)


def test_request_id_is_generated_by_server_and_unique(client):
    first = client.get("/health", headers={REQUEST_ID_HEADER: "forged-by-client"})
    second = client.get("/health")
    assert first.status_code == 200 and "request_id" not in first.json()
    assert first.headers[REQUEST_ID_HEADER] != "forged-by-client"
    assert first.headers[REQUEST_ID_HEADER] != second.headers[REQUEST_ID_HEADER]


def test_request_id_header_is_exposed_to_browsers(client):
    r = client.options(
        "/api/v1/applications",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert r.status_code == 200
    r = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert REQUEST_ID_HEADER in r.headers["access-control-expose-headers"]


def test_access_log_uses_parametrised_route_and_no_personal_data(client, caplog):
    headers = login(client, ADMIN)
    application = client.get("/api/v1/applications", headers=headers).json()["items"][0]
    with caplog.at_level(logging.INFO, logger="app.access"):
        r = client.get(f"/api/v1/applications/{application['id']}", headers=headers, params={"q": SENSITIVE})
    assert r.status_code == 200
    text = "\n".join(rec.getMessage() for rec in caplog.records if rec.name == "app.access")
    assert "GET /applications/{application_id} -> 200" in text  # router-relative template, not the raw path
    assert r.headers[REQUEST_ID_HEADER] in text
    assert application["id"] not in text and SENSITIVE not in text and "Bearer" not in text


def test_audited_routes_still_work_and_stay_admin_only(client, db):
    assert client.get("/api/v1/audit-events").status_code == 401
    assert client.get("/api/v1/audit-events", headers=login(client, CAPT_IA)).status_code == 403
    r = client.get("/api/v1/audit-events", headers=login(client, ADMIN))
    assert r.status_code == 200 and isinstance(r.json(), list)
    assert REQUEST_ID_HEADER in r.headers


@pytest.fixture
def boom_client():
    """Isolated app: only the error layer, plus routes that fail in controlled ways."""
    app = FastAPI()
    install_error_handling(app)

    class Payload(BaseModel):
        value: int

    @app.get("/boom/{secret_id}")
    def boom(secret_id: str):
        raise RuntimeError(f"fallo con dato personal {SENSITIVE} {secret_id}")

    @app.post("/validate")
    def validate(payload: Payload):
        return payload

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def test_500_is_generic_correlated_and_logs_only_the_error_class(boom_client, caplog):
    with caplog.at_level(logging.INFO, logger="app.access"):
        r = boom_client.get("/boom/abc-123")
    assert r.status_code == 500
    assert r.json()["detail"] == INTERNAL_ERROR_DETAIL
    request_id = assert_correlated(r)
    assert SENSITIVE not in r.text and "abc-123" not in r.text and "RuntimeError" not in r.text
    logged = "\n".join(rec.getMessage() for rec in caplog.records if rec.name == "app.access")
    assert "unhandled RuntimeError on GET /boom/{secret_id}" in logged
    assert request_id in logged
    assert SENSITIVE not in logged and "abc-123" not in logged
    assert all(rec.exc_info is None for rec in caplog.records if rec.name == "app.access")


def test_422_never_echoes_input_even_on_type_errors(boom_client):
    r = boom_client.post("/validate", json={"value": SENSITIVE})
    assert r.status_code == 422
    assert SENSITIVE not in r.text
    assert_correlated(r)
