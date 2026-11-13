import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.modules.audit.models import AuditEvent
from tests.conftest import ADMIN, CAPT_IA, login


def first_ia(client, h):
    return client.get("/api/v1/applications", headers=h).json()["items"][0]


def test_crm_event_is_recorded_with_author_and_audited(client, db):
    h = login(client, CAPT_IA)
    a = first_ia(client, h)
    r = client.post(f"/api/v1/applications/{a['id']}/events", headers=h, json={"tipo": "contacto", "canal": "telefono", "resumen": "Llamada para confirmar asistencia a la jornada"})
    assert r.status_code == 201 and r.json()["actor"] == "Captación IA (demo)"
    detail = client.get(f"/api/v1/applications/{a['id']}", headers=h).json()
    assert [e["tipo"] for e in detail["events"]] == ["creada", "contacto"]
    added = db.scalar(select(AuditEvent).where(AuditEvent.action == "application.event_added"))
    assert added.meta == {"codigo": a["codigo"], "tipo": "contacto"}  # no free text in audit
    assert db.scalar(select(AuditEvent).where(AuditEvent.action == "application.viewed")) is not None


def test_crm_event_validation(client):
    h = login(client, CAPT_IA)
    a = first_ia(client, h)
    url = f"/api/v1/applications/{a['id']}/events"
    assert client.post(url, headers=h, json={"tipo": "nota", "resumen": "x" * 501}).status_code == 422
    # stage changes are reserved for the human review/decision endpoints (F2)
    assert client.post(url, headers=h, json={"tipo": "cambio_etapa", "resumen": "admitida"}).status_code == 422
    assert client.post(url, headers=h, json={"tipo": "nota", "canal": "whatsapp", "resumen": "x"}).status_code == 422


def test_audit_trail_is_append_only(client, db):
    login(client, ADMIN)
    with pytest.raises(DBAPIError):
        db.execute(text("UPDATE audit_event SET action = 'manipulado'"))
        db.commit()
    db.rollback()
    with pytest.raises(DBAPIError):
        db.execute(text("DELETE FROM audit_event"))
        db.commit()
    db.rollback()


def test_failed_login_is_audited_without_identifiers(client, db):
    client.post("/api/v1/auth/login", json={"email": "alguien@example.test", "password": "mal"})
    ev = db.scalar(select(AuditEvent).where(AuditEvent.action == "auth.login_failed"))
    assert ev.target_id is None and ev.meta == {}
