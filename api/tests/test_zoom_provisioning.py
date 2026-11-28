"""Exercise committed provisioning intent across independent PostgreSQL sessions."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from threading import Event
from unittest.mock import Mock

from sqlalchemy import select

from app.core.config import settings
from app.core.db import SessionLocal
from app.modules.attendance.models import AttendanceSession
from app.modules.audit.models import AuditEvent
from app.modules.identity.models import User
from app.modules.zoom import router as zoom_router
from app.modules.zoom.client import ZoomError
from tests.conftest import ADMIN, DOCENTE, login


def test_provisioning_survives_lost_response_and_is_reconciled_once(client, monkeypatch):
    monkeypatch.setattr(settings, "zoom_enabled", True)
    monkeypatch.setattr(settings, "zoom_provisioning_enabled", True)
    monkeypatch.setattr(settings, "zoom_host_id", "synthetic-host")
    with SessionLocal() as db:
        creator = db.scalar(select(User).where(User.email == DOCENTE))
        session = AttendanceSession(cohort_id="COH-IA", session_date=date(2027, 1, 2),
                                    shift="completa", duration_fraction=Decimal("1"), created_by=creator.id)
        db.add(session)
        db.flush()
        session_id = session.id
        db.commit()

    teacher = login(client, DOCENTE)
    admin = login(client, ADMIN)
    started, release = Event(), Event()
    provider = Mock()
    provider.config = settings

    def accepted_then_disconnected(*args, **kwargs):
        started.set()
        assert release.wait(10)
        raise ZoomError("Synthetic connection lost after acceptance")

    provider.create_meeting.side_effect = accepted_then_disconnected
    provider.recover_meeting.return_value = {"id": "123456789", "join_url": "https://zoom.us/j/123456789"}
    monkeypatch.setattr(zoom_router, "ZoomClient", lambda *_: provider)
    base = f"/api/v1/attendance-sessions/{session_id}/zoom"
    body = {"topic": "Synthetic lesson", "start_at": "2027-01-02T12:00:00Z", "duration_minutes": 60}

    with ThreadPoolExecutor(1) as pool:
        future = pool.submit(client.post, base + "/meeting", headers=teacher, json=body)
        try:
            assert started.wait(10)
            pending = client.get(base + "/provisioning", headers=teacher)
            assert pending.status_code == 200, pending.text
            assert pending.json()["state"] == "pending"
            assert client.post(base + "/meeting", headers=teacher, json=body).status_code == 409
        finally:
            release.set()
        assert future.result(timeout=10).status_code == 502

    uncertain = client.get(base + "/provisioning", headers=teacher).json()
    assert uncertain == {**pending.json(), "state": "uncertain"}
    assert client.post(base + "/meeting", headers=teacher, json=body).status_code == 409
    provider.create_meeting.assert_called_once()
    assert str(provider.create_meeting.call_args.kwargs["operation_id"]) == uncertain["operation_id"]

    reconcile = base + "/provisioning/reconcile"
    recovered = {"operation_id": uncertain["operation_id"], "provider_id": "123456789"}
    assert client.post(reconcile, headers=teacher, json=recovered).status_code == 403
    provider.recover_meeting.assert_not_called()
    provider.recover_meeting.side_effect = ZoomError("No matching synthetic meeting")
    assert client.post(reconcile, headers=admin, json=recovered).status_code == 409
    assert client.get(base + "/provisioning", headers=teacher).json() == uncertain
    assert client.get(base + "/meeting", headers=teacher).json() is None
    assert client.post(base + "/meeting", headers=teacher, json=body).status_code == 409
    provider.create_meeting.assert_called_once()

    provider.recover_meeting.side_effect = None
    provider.recover_meeting.reset_mock()
    result = client.post(reconcile, headers=admin, json=recovered)
    assert result.status_code == 200, result.text
    assert client.post(reconcile, headers=admin, json=recovered).json() == result.json()
    provider.recover_meeting.assert_called_once()
    assert client.get(base + "/meeting", headers=teacher).json() == result.json()
    assert client.get(base + "/provisioning", headers=teacher).json()["state"] == "confirmed"
    with SessionLocal() as db:
        rows = db.scalars(select(AuditEvent).where(
            AuditEvent.target_id == str(session_id), AuditEvent.action.startswith("zoom.provisioning_"),
        ).order_by(AuditEvent.id)).all()
        assert [row.action for row in rows] == [
            "zoom.provisioning_pending", "zoom.provisioning_uncertain", "zoom.provisioning_confirmed",
        ]
        assert rows[0].actor_user_id == rows[1].actor_user_id != rows[2].actor_user_id
