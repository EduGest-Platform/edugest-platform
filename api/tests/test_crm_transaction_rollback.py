"""KAN-127: CRM event and success audit must commit or roll back together."""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import audit
from app.core.db import SessionLocal
from app.main import app
from app.modules.admissions.models import Application, ApplicationEvent
from app.modules.audit.models import AuditEvent
from tests.conftest import CAPT_IA, login, new_application


def stored(application_id):
    # Observe persistence through a new session, not the failed request's identity map.
    with SessionLocal() as db:
        application = db.get(Application, uuid.UUID(application_id))
        events = set(db.scalars(select(ApplicationEvent.id).where(ApplicationEvent.application_id == application.id)))
        audits = set(db.scalars(select(AuditEvent.id).where(
            AuditEvent.action == "application.event_added", AuditEvent.target_id == application_id,
        )))
        return application.stage, application.person_id, events, audits


@pytest.mark.parametrize("failure_point", ["flush", "audit", "commit"])
def test_failed_crm_write_has_no_partial_event_or_success_audit_and_can_recover(client, monkeypatch, failure_point):
    receipt = client.post("/api/v1/applications", json=new_application(email="crm.rollback@example.test"))
    assert receipt.status_code == 201
    application_id = receipt.json()["id"]
    actor = login(client, CAPT_IA)
    path = f"/api/v1/applications/{application_id}/events"
    body = {"tipo": "contacto", "canal": "telefono", "resultado": "respondida", "resumen": "Synthetic operational contact"}
    before = stored(application_id)

    def fail(*_args, **_kwargs):
        raise RuntimeError("Synthetic CRM persistence failure")

    original_flush = Session.flush
    original_record = audit.record

    def flush(db, *args, **kwargs):
        if any(isinstance(item, ApplicationEvent) for item in db.new):
            fail()
        return original_flush(db, *args, **kwargs)

    def record(db, principal, action, *args, **kwargs):
        if action == "application.event_added":
            fail()
        return original_record(db, principal, action, *args, **kwargs)

    with TestClient(app, raise_server_exceptions=False) as failing_client:
        with monkeypatch.context() as patch:
            if failure_point == "flush":
                patch.setattr(Session, "flush", flush)
            elif failure_point == "audit":
                patch.setattr(audit, "record", record)
            else:
                patch.setattr(Session, "commit", fail)
            assert failing_client.post(path, headers=actor, json=body).status_code == 500

    assert stored(application_id) == before
    recovery = client.post(path, headers=actor, json=body)
    assert recovery.status_code == 201
    stage, person_id, events, audits = stored(application_id)
    assert (stage, person_id) == before[:2]
    assert len(events - before[2]) == len(audits - before[3]) == 1
    assert uuid.UUID(recovery.json()["id"]) in events
    with SessionLocal() as db:
        row = db.scalars(select(AuditEvent).where(AuditEvent.id.in_(audits - before[3]))).one()
        assert row.actor_user_id is not None
        assert row.meta == {"codigo": receipt.json()["codigo"], "tipo": "contacto"}
        assert body["resumen"] not in str(row.meta)
