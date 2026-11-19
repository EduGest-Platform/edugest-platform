"""KAN-105: uniform errors, server-side request IDs, no data leakage in bodies or logs."""

import asyncio
import logging
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
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
    r = client.get("/api/v1/audit-events", headers=login(client, CAPT_IA))
    assert r.status_code == 403
    assert r.json()["detail"]
    assert_correlated(r)


def test_out_of_scope_application_is_indistinguishable_from_an_unknown_one(client):
    """PO decision 19/11/2026: an existing application outside the scope answers like an unknown id."""
    ia_headers = login(client, CAPT_IA)
    other = login(client, ADMIN)
    data_app = next(a for a in client.get("/api/v1/applications", headers=other, params={"limit": 200}).json()["items"] if a["program_id"] == "P-DATA")
    foreign = client.get(f"/api/v1/applications/{data_app['id']}", headers=ia_headers)
    unknown = client.get("/api/v1/applications/00000000-0000-0000-0000-000000000000", headers=ia_headers)
    assert foreign.status_code == unknown.status_code == 404
    assert foreign.json()["detail"] == unknown.json()["detail"]
    assert_correlated(foreign)


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
    assert "GET /boom/{secret_id} -> 500" in logged  # the access line is still written for failures


def test_500_keeps_cors_headers_so_browsers_can_read_the_request_id(caplog):
    app = FastAPI()
    install_error_handling(app)
    app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], expose_headers=[REQUEST_ID_HEADER])

    @app.get("/boom")
    def boom():
        raise RuntimeError(SENSITIVE)

    with TestClient(app, raise_server_exceptions=False) as c:
        r = c.get("/boom", headers={"Origin": "http://localhost:5173"})
    assert r.status_code == 500
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert_correlated(r)


def test_access_logger_emits_info_without_extra_logging_setup():
    assert logging.getLogger("app.access").getEffectiveLevel() <= logging.INFO
    assert logging.getLogger("app.access").handlers


def test_entrypoint_disables_uvicorn_access_log():
    entrypoint = Path(__file__).resolve().parents[1] / "docker-entrypoint.sh"
    assert "--no-access-log" in entrypoint.read_text(encoding="utf-8")


def test_422_never_echoes_input_even_on_type_errors(boom_client):
    r = boom_client.post("/validate", json={"value": SENSITIVE})
    assert r.status_code == 422
    assert SENSITIVE not in r.text
    assert_correlated(r)


def test_error_after_response_started_logs_only_the_class_and_is_not_reraised(caplog):
    """A 500 is impossible once headers are sent. The server must not print a traceback with the exception message."""
    app = FastAPI()
    install_error_handling(app)

    @app.get("/stream/{secret_id}")
    def stream(secret_id: str):
        def chunks():
            yield b"first-chunk"
            raise RuntimeError(f"fallo con dato personal {SENSITIVE} {secret_id}")

        return StreamingResponse(chunks())

    sent: list[dict] = []

    request_delivered = False

    async def receive():
        nonlocal request_delivered
        if not request_delivered:
            request_delivered = True
            return {"type": "http.request", "body": b"", "more_body": False}
        await asyncio.sleep(3600)  # StreamingResponse listens for a disconnect; an idle client never sends one

    async def send(message):
        sent.append(message)

    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "GET", "scheme": "http",
        "path": "/stream/abc-123", "raw_path": b"/stream/abc-123", "query_string": f"email={SENSITIVE}".encode(),
        "root_path": "", "headers": [], "client": ("testclient", 50000), "server": ("testserver", 80),
    }
    with caplog.at_level(logging.INFO, logger="app.access"):
        asyncio.run(app(scope, receive, send))  # must not raise: re-raising would make the server log the traceback

    assert sent[0]["type"] == "http.response.start" and sent[0]["status"] == 200
    assert any(m["type"] == "http.response.body" and m["body"] == b"first-chunk" for m in sent)
    # No final empty body: the connection must look truncated, not completed.
    assert not any(m["type"] == "http.response.body" and not m.get("more_body", False) for m in sent)
    request_id = dict(sent[0]["headers"])[REQUEST_ID_HEADER.lower().encode()].decode()
    logged = "\n".join(rec.getMessage() for rec in caplog.records if rec.name == "app.access")
    assert "unhandled RuntimeError on GET /stream/{secret_id}" in logged
    assert request_id in logged
    assert SENSITIVE not in logged and "abc-123" not in logged and "fallo con dato personal" not in logged
    assert all(rec.exc_info is None for rec in caplog.records if rec.name == "app.access")
