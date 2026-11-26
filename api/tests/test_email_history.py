from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.dialects import postgresql

from app.modules.email import access


def test_history_is_scoped_and_excludes_message_content():
    db = MagicMock()
    principal = SimpleNamespace(user=SimpleNamespace(id=uuid4()))
    now = datetime.now(timezone.utc)
    message_id = uuid4()
    db.execute.return_value = [(message_id, "uncertain", 1, now, now, None)]
    with patch.object(access, "require_cohort") as require:
        result = access.list_notification_history(db, principal, cohort_id="cohort-a")
    require.assert_called_once_with(db, principal, access.EMAIL_SEND_PERMISSION, "cohort-a")
    statement = db.execute.call_args.args[0]
    compiled = statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)
    assert "email_outbox.cohort_id =" in sql
    assert "email_outbox.created_by =" in sql
    assert "cohort-a" in compiled.params.values()
    assert principal.user.id in compiled.params.values()
    assert 50 in compiled.params.values()
    assert "recipient" not in sql
    assert "text_body" not in sql
    assert "html_body" not in sql
    assert result == [access.NotificationHistoryItem(message_id, "uncertain", 1, now, now, None)]


def test_forbidden_history_never_queries():
    db = MagicMock()
    with patch.object(access, "require_cohort", side_effect=HTTPException(403)):
        with pytest.raises(HTTPException):
            access.list_notification_history(db, MagicMock(), cohort_id="other")
    db.execute.assert_not_called()


@pytest.mark.parametrize("limit", [0, 101])
def test_history_limit(limit):
    db = MagicMock()
    with patch.object(access, "require_cohort"):
        with pytest.raises(ValueError):
            access.list_notification_history(db, MagicMock(), cohort_id="cohort-a", limit=limit)
    db.execute.assert_not_called()


@pytest.mark.parametrize("status", ["sending", "sent", "failed", "uncertain"])
def test_cancel_rejects_non_pending(status):
    db = MagicMock()
    message = SimpleNamespace(status=status)
    db.scalars.return_value.one_or_none.return_value = message
    with patch.object(access, "require_cohort"), patch.object(access.audit, "record") as audit:
        with pytest.raises(access.UserFacingError):
            access.cancel_notification(db, MagicMock(), cohort_id="cohort-a", message_id=uuid4())
    assert message.status == status
    audit.assert_not_called()
    db.flush.assert_not_called()


def test_cancel_pending_is_scoped_locked_and_idempotent():
    db = MagicMock()
    principal = SimpleNamespace(user=SimpleNamespace(id=uuid4()))
    message_id = uuid4()
    message = SimpleNamespace(status="pending")
    db.scalars.return_value.one_or_none.return_value = message
    with patch.object(access, "require_cohort") as require, patch.object(access.audit, "record") as audit:
        for _ in range(2):
            access.cancel_notification(db, principal, cohort_id="cohort-a", message_id=message_id)
        assert require.call_count == 2
        audit.assert_called_once()
    compiled = db.scalars.call_args.args[0].compile(dialect=postgresql.dialect())
    assert "FOR UPDATE" in str(compiled)
    assert "email_outbox.created_by =" in str(compiled)
    assert "email_outbox.cohort_id =" in str(compiled)
    assert principal.user.id in compiled.params.values()
    assert message_id in compiled.params.values()
    assert message.status == "cancelled"
    db.flush.assert_called_once()


def test_cancel_forbidden_never_queries():
    db = MagicMock()
    with patch.object(access, "require_cohort", side_effect=HTTPException(403)):
        with pytest.raises(HTTPException):
            access.cancel_notification(db, MagicMock(), cohort_id="other", message_id=uuid4())
    db.scalars.assert_not_called()
