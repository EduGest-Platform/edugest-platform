from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.main import app
from app.modules.admissions.models import Application, ApplicationEvent
from app.modules.audit.models import AuditEvent
from app.modules.identity.models import Person
from tests.conftest import ASPIRANTE, login, new_application


def count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def test_public_inscription_creates_person_application_event_and_audit(client, db):
    persons = count(db, Person)
    r = client.post("/api/v1/applications", json=new_application())
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["codigo"] == "IA27A-0007" and body["stage"] == "enviada"
    assert "email" not in body  # receipt does not echo personal data
    assert count(db, Person) == persons + 1
    app_id = body["id"]
    assert db.scalar(select(func.count()).select_from(ApplicationEvent).where(ApplicationEvent.application_id == app_id)) == 1
    ev = db.scalar(select(AuditEvent).where(AuditEvent.action == "application.created"))
    assert ev.target_id == app_id and "email" not in ev.meta and "nombre" not in ev.meta


def test_duplicate_in_same_call_is_rejected_after_normalisation(client, db):
    assert client.post("/api/v1/applications", json=new_application()).status_code == 201
    total = count(db, Application)
    r = client.post("/api/v1/applications", json=new_application(email="  NUEVA.Persona@Example.test "))
    assert r.status_code == 409
    assert count(db, Application) == total


def test_same_person_reused_across_calls(client, db):
    a = client.post("/api/v1/applications", json=new_application()).json()
    persons = count(db, Person)
    b = client.post("/api/v1/applications", json=new_application(call_id="CONV-DATA-2027A", nombre="Otro nombre")).json()
    assert b["codigo"].startswith("DA27A-")
    assert count(db, Person) == persons
    pa = db.scalar(select(Application.person_id).where(Application.id == a["id"]))
    pb = db.scalar(select(Application.person_id).where(Application.id == b["id"]))
    assert pa == pb


def test_validation_and_closed_calls(client):
    assert client.post("/api/v1/applications", json=new_application(acepta_datos_sinteticos=False)).status_code == 422
    assert client.post("/api/v1/applications", json=new_application(email="no-es-un-correo")).status_code == 422
    assert client.post("/api/v1/applications", json=new_application(motivacion="corta")).status_code == 422
    assert client.post("/api/v1/applications", json=new_application(call_id="CONV-IA-2026B")).status_code == 409
    assert client.post("/api/v1/applications", json=new_application(call_id="NO-EXISTE")).status_code == 404


def test_seeded_aspirant_applies_and_sees_only_own_minimal_view(client):
    h = login(client, ASPIRANTE)
    assert client.get("/api/v1/me/applications", headers=h).json() == []
    r = client.post("/api/v1/applications", json=new_application(email=ASPIRANTE, nombre="Alex Roca"), headers=h)
    assert r.status_code == 201
    mine = client.get("/api/v1/me/applications", headers=h).json()
    assert [m["codigo"] for m in mine] == [r.json()["codigo"]]
    assert set(mine[0]) == {"id", "codigo", "call_id", "call_nombre", "stage", "created_at", "updated_at"}
    assert client.get("/api/v1/auth/me", headers=h).json()["application_ids"] == [r.json()["id"]]


def test_concurrent_inscriptions_get_unique_codes():
    def submit(i):
        with TestClient(app) as c:
            return c.post("/api/v1/applications", json=new_application(email=f"concurrente{i}@example.test")).json()["codigo"]

    with ThreadPoolExecutor(max_workers=6) as ex:
        codes = list(ex.map(submit, range(6)))
    assert len(set(codes)) == 6
