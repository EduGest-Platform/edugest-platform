from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.modules.email.queue import claim_next, finish_claim, recover_interrupted, schedule_retry

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def item(**overrides):
    values = dict(id=uuid4(), status="pending", attempts=0, claimed_at=None,
                  sent_at=None, error_code=None, available_at=NOW)
    values.update(overrides)
    return SimpleNamespace(**values)


def test_claim():
    db = MagicMock()
    message = item()
    db.scalars.return_value.first.return_value = message
    assert claim_next(db, now=NOW) is message
    assert (message.status, message.attempts, message.claimed_at) == ("sending", 1, NOW)
    db.flush.assert_called_once()


@pytest.mark.parametrize("outcome,status,code", [
    ("sent", "sent", None),
    ("failed", "failed", "delivery_failed"),
    ("uncertain", "uncertain", "delivery_unknown"),
    ("transient_pre_send", "failed", "transient_pre_send"),
])
def test_finish(outcome, status, code):
    db = MagicMock()
    message = item(status="sending", attempts=1)
    db.scalars.return_value.one.return_value = message
    finish_claim(db, message_id=message.id, attempt=1, outcome=outcome, now=NOW)
    assert (message.status, message.error_code) == (status, code)
    assert message.sent_at == (NOW if outcome == "sent" else None)


def test_stale_claim_rejected():
    db = MagicMock()
    db.scalars.return_value.one.return_value = item(status="sending", attempts=2)
    with pytest.raises(ValueError, match="Stale"):
        finish_claim(db, message_id=uuid4(), attempt=1, outcome="sent", now=NOW)
    db.flush.assert_not_called()


@pytest.mark.parametrize("attempt,delay", [(1, 60), (2, 120), (3, None)])
def test_retry_limit(attempt, delay):
    db = MagicMock()
    message = item(status="failed", attempts=attempt, error_code="transient_pre_send")
    db.scalars.return_value.one.return_value = message
    assert schedule_retry(db, message_id=message.id, now=NOW) == (delay is not None)
    if delay is not None:
        assert message.available_at == NOW + timedelta(seconds=delay)
        assert message.status == "pending"
    else:
        assert message.status == "failed"
        db.flush.assert_not_called()


@pytest.mark.parametrize("status,code", [("uncertain", "delivery_unknown"), ("failed", "delivery_failed")])
def test_unsafe_retry_rejected(status, code):
    db = MagicMock()
    message = item(status=status, attempts=1, error_code=code)
    db.scalars.return_value.one.return_value = message
    assert not schedule_retry(db, message_id=message.id, now=NOW)
    db.flush.assert_not_called()


def test_recovery_quarantines_claims():
    db = MagicMock()
    message = item(status="sending", attempts=1, claimed_at=NOW - timedelta(hours=1))
    db.scalars.return_value = [message]
    assert recover_interrupted(db, cutoff=NOW) == 1
    assert (message.status, message.error_code, message.attempts) == ("uncertain", "claim_interrupted", 1)
    db.flush.assert_called_once()
