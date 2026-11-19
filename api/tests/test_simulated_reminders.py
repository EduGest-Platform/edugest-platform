"""KAN-129: simulations are durable evidence, never deliveries or decisions."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import func, inspect, select, text

from app.core import audit
from app.core.db import engine
from app.main import app
from app.modules.admissions.models import Application, ApplicationEvent
from app.modules.audit.models import AuditEvent
from app.modules.automation.models import SimulatedReminder
from app.modules.learning.models import Enrollment
from tests.conftest import ADMIN, API_DIR, ASPIRANTE, CAPT_DATA, CAPT_IA, CODER, COORD, DOCENTE, SEL_IA, login


@pytest.fixture
def simulation(client, db, monkeypatch):
    monkeypatch.setattr("app.modules.automation.reminders.utcnow", lambda: datetime(2026, 11, 19, 12, tzinfo=timezone.utc))
    application = db.scalar(select(Application).where(Application.call_id == "CONV-IA-2027A",
                                                      Application.stage.in_(["enviada", "requisitos_en_revision"])))
    assert application is not None
    return application, f"/api/v1/applications/{application.id}/simulated-reminders"


def payload(**overrides):
    return {"task_ref": "synthetic-docs-v1", "kind": "documentation", "due_at": "2026-11-19T12:00:00Z",
            "synthetic_only": True, **overrides}


def counts(db):
    db.expire_all()
    return (db.scalar(select(func.count()).select_from(SimulatedReminder)),
            db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action == "simulated_reminder.recorded")))


@pytest.mark.parametrize("email", [ADMIN, CAPT_IA, SEL_IA])
def test_create_retry_history_and_no_business_writes(client, db, simulation, email):
    application, url = simulation
    headers = login(client, email)
    before = (application.stage, db.scalar(select(func.count()).select_from(ApplicationEvent)),
              db.scalar(select(func.count()).select_from(Enrollment)))
    first = client.post(url, headers=headers, json=payload())
    assert first.status_code == 201, first.text
    data = first.json()
    assert data["simulated_only"] and data["reminder"]["simulated_only"]
    assert data["reminder"]["schedule_source"] == "staff_entered"
    assert not {"recorded_by", "recipient", "email", "delivered_at", "idempotency_key"} & data["reminder"].keys()
    with TestClient(app) as other:
        retry = other.post(url, headers=login(other, ADMIN), json=payload(due_at="2026-11-19T14:00:00+02:00"))
        assert retry.status_code == 200 and retry.json() == data
    history = client.get(url, headers=headers).json()
    assert history["items"] == [data["reminder"]] and history["total"] == 1
    assert counts(db) == (1, 1)
    assert (db.get(Application, application.id).stage,
            db.scalar(select(func.count()).select_from(ApplicationEvent)),
            db.scalar(select(func.count()).select_from(Enrollment))) == before


def test_not_due_then_boundary_and_distinct_schedule_kind(client, db, simulation, monkeypatch):
    _, url = simulation
    headers = login(client, ADMIN)
    future = payload(due_at="2026-11-19T12:00:01Z")
    response = client.post(url, headers=headers, json=future)
    assert response.status_code == 200 and response.json()["outcome"] == "not_due"
    assert response.json()["reminder"] is None and counts(db) == (0, 0)
    monkeypatch.setattr("app.modules.automation.reminders.utcnow", lambda: datetime(2026, 11, 19, 12, 0, 1, tzinfo=timezone.utc))
    assert client.post(url, headers=headers, json=future).status_code == 201
    assert client.post(url, headers=headers, json=payload()).status_code == 201
    assert client.post(url, headers=headers, json=payload(kind="exercises")).status_code == 201
    result = client.get(url + "?limit=1", headers=headers).json()
    assert result["total"] == 3 and len(result["items"]) == 1 and result["limit"] == 1
    assert counts(db) == (3, 3)


@pytest.mark.parametrize("email", [CAPT_DATA, COORD, DOCENTE, ASPIRANTE, CODER])
def test_denied_roles_and_scope_leave_no_simulation(client, db, simulation, email):
    _, url = simulation
    headers = login(client, email)
    assert client.post(url, headers=headers, json=payload()).status_code == 403
    assert client.get(url, headers=headers).status_code == 403
    assert counts(db) == (0, 0)


@pytest.mark.parametrize("overrides", [{"kind": "response"}, {"kind": "interview"}, {"synthetic_only": False},
                                       {"due_at": "2026-11-19T12:00:00"}, {"task_ref": "person@example.test"},
                                       {"recorded_by": "forged"}, {"delivered_at": "2026-11-19T12:00:00Z"}])
def test_invalid_or_forged_input(client, db, simulation, overrides):
    _, url = simulation
    assert client.post(url, headers=login(client, ADMIN), json=payload(**overrides)).status_code == 422
    assert counts(db) == (0, 0)


def test_anonymous_and_outside_preselection(client, db, simulation):
    application, url = simulation
    assert client.post(url, json=payload()).status_code == 401
    assert client.get(url).status_code == 401
    application.stage = "retirada"
    db.commit()
    assert client.post(url, headers=login(client, ADMIN), json=payload()).status_code == 409
    assert counts(db) == (0, 0)


def test_concurrent_retry_is_one_simulation_and_audit(client, db, simulation):
    _, url = simulation
    headers = login(client, ADMIN)
    def send(_):
        with TestClient(app) as other:
            return other.post(url, headers=headers, json=payload())
    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(send, range(2)))
    assert sorted(response.status_code for response in responses) == [200, 201]
    assert responses[0].json() == responses[1].json()
    assert counts(db) == (1, 1)


def test_audit_failure_rolls_back_simulation(client, db, simulation, monkeypatch):
    _, url = simulation
    headers = login(client, ADMIN)
    original = audit.record
    def fail(*args, **kwargs):
        if args[2] == "simulated_reminder.recorded":
            raise RuntimeError("synthetic audit failure")
        return original(*args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(audit, "record", fail)
        response = client.post(url, headers=headers, json=payload())
        assert response.status_code == 500
    assert counts(db) == (0, 0)
    assert client.post(url, headers=headers, json=payload()).status_code == 201
    assert counts(db) == (1, 1)


def test_application_deletion_cascades(client, db, simulation):
    application, url = simulation
    assert client.post(url, headers=login(client, ADMIN), json=payload()).status_code == 201
    db.execute(text("DELETE FROM application WHERE id=:id"), {"id": application.id})
    db.commit()
    assert counts(db) == (0, 1)


def test_reminder_migration_roundtrip_preserves_preselection_and_execution_tables():
    cfg = Config(API_DIR + "/alembic.ini")
    cfg.set_main_option("script_location", API_DIR + "/alembic")
    try:
        command.downgrade(cfg, "0005")
        tables = set(inspect(engine).get_table_names())
        assert "simulated_reminder" not in tables
        assert {"preselection_decision", "automation_execution", "call_requirement", "knowledge_document"} <= tables
    finally:
        command.upgrade(cfg, "head")
    assert "simulated_reminder" in inspect(engine).get_table_names()
