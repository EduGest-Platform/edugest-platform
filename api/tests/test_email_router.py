from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.deps import current_principal, get_db
from app.core.error_handling import install_error_handling
from app.modules.email import router as email


@pytest.fixture
def context():
    app = FastAPI()
    install_error_handling(app)
    app.include_router(email.router, prefix="/api/v1")
    db = MagicMock()
    principal = SimpleNamespace()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[current_principal] = lambda: principal
    payload = dict(enrollment_id=str(uuid4()), idempotency_key="synthetic-1",
                   topic="Synthetic class", available_at="2027-01-01T09:00:00Z")
    with TestClient(app) as client, patch.object(email, "settings", SimpleNamespace(
        email_enabled=True
    )), patch.object(email, "enqueue_academic_notification") as enqueue:
        enqueue.return_value = uuid4()
        yield app, client, db, enqueue, payload


URL = "/api/v1/cohorts/synthetic-cohort/email/notifications"


def test_accepts_notification(context):
    _, client, db, enqueue, payload = context
    response = client.post(URL, json=payload)
    assert response.status_code == 202
    assert response.json() == {"message_id": str(enqueue.return_value)}
    assert enqueue.call_args.kwargs["cohort_id"] == "synthetic-cohort"
    db.commit.assert_called_once()


@pytest.mark.parametrize("field,value", [
    ("enrollment_id", "invalid"),
    ("topic", ""),
    ("idempotency_key", ""),
    ("available_at", "2027-01-01T09:00:00"),
    ("recipient", "arbitrary@example.invalid"),
])
def test_invalid_request_never_enqueues(context, field, value):
    _, client, db, enqueue, payload = context
    payload[field] = value
    assert client.post(URL, json=payload).status_code == 422
    enqueue.assert_not_called()
    db.commit.assert_not_called()


def test_disabled_integration(context):
    _, client, db, enqueue, payload = context
    email.settings.email_enabled = False
    assert client.post(URL, json=payload).status_code == 404
    enqueue.assert_not_called()
    db.commit.assert_not_called()


def test_unauthenticated(context):
    app, client, db, enqueue, payload = context
    def reject():
        raise HTTPException(401, "Unauthorized")
    app.dependency_overrides[current_principal] = reject
    assert client.post(URL, json=payload).status_code == 401
    enqueue.assert_not_called()
    db.commit.assert_not_called()


def test_forbidden(context):
    _, client, db, enqueue, payload = context
    enqueue.side_effect = HTTPException(403, "Forbidden")
    assert client.post(URL, json=payload).status_code == 403
    db.commit.assert_not_called()


def test_invalid_enqueue_rolls_back(context):
    _, client, db, enqueue, payload = context
    enqueue.side_effect = ValueError("synthetic conflict")
    response = client.post(URL, json=payload)
    assert response.status_code == 422
    assert "synthetic conflict" not in response.text
    db.rollback.assert_called_once()
    db.commit.assert_not_called()


def test_notification_history(context):
    from datetime import datetime, timezone
    from app.modules.email.access import NotificationHistoryItem

    _, client, db, _, _ = context
    now = datetime.now(timezone.utc)
    message_id = uuid4()
    with patch.object(email, "list_notification_history", return_value=[
        NotificationHistoryItem(message_id, "pending", 0, now, now, None)
    ]) as history:
        response = client.get(URL)
    assert response.status_code == 200
    assert response.json()[0]["message_id"] == str(message_id)
    assert response.json()[0]["status"] == "pending"
    assert set(response.json()[0]) == {"message_id", "status", "attempts", "created_at", "available_at", "sent_at"}
    assert history.call_args.kwargs["cohort_id"] == "synthetic-cohort"
    db.commit.assert_not_called()


def test_notification_history_forbidden(context):
    _, client, _, _, _ = context
    with patch.object(email, "list_notification_history", side_effect=HTTPException(403)):
        assert client.get(URL).status_code == 403
