from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.errors import UserFacingError
from app.modules.email import access


def setup():
    db = MagicMock()
    principal = SimpleNamespace(user=SimpleNamespace(id=uuid4()))
    enrollment = SimpleNamespace(cohort_id="synthetic-cohort", estado="activa", person_id=uuid4())
    person = SimpleNamespace(email="student@example.invalid")
    db.get.side_effect = [enrollment, person]
    args = dict(cohort_id=enrollment.cohort_id, enrollment_id=uuid4(),
                idempotency_key="synthetic-notification", topic="Synthetic class",
                available_at=datetime(2027, 1, 1, tzinfo=timezone.utc))
    return db, principal, enrollment, person, args


def test_scoped_notification_resolves_recipient_and_audits():
    db, principal, enrollment, person, args = setup()
    with patch.object(access, "require_cohort") as require, patch.object(
        access, "enqueue"
    ) as enqueue, patch.object(access.audit, "record") as record:
        enqueue.return_value = uuid4()
        result = access.enqueue_academic_notification(db, principal, **args)
    require.assert_called_once_with(db, principal, "email.send", enrollment.cohort_id)
    assert enqueue.call_args.kwargs["recipient"] == person.email
    assert enqueue.call_args.kwargs["created_by"] == principal.user.id
    assert result == enqueue.return_value
    record.assert_called_once_with(db, principal, "email.enqueue_requested", "email_outbox",
                                   str(result), cohort_id=enrollment.cohort_id)
    db.commit.assert_not_called()


@pytest.mark.parametrize("case", ["denied", "missing", "other_cohort", "inactive", "missing_person"])
def test_rejected_notification_never_enqueues(case):
    db, principal, enrollment, person, args = setup()
    with patch.object(access, "require_cohort") as require, patch.object(
        access, "enqueue"
    ) as enqueue, patch.object(access.audit, "record") as record:
        if case == "denied":
            require.side_effect = UserFacingError(403, "forbidden", "Forbidden")
        elif case == "missing":
            db.get.side_effect = [None]
        elif case == "other_cohort":
            enrollment.cohort_id = "other-cohort"
        elif case == "inactive":
            enrollment.estado = "finalizada"
        else:
            db.get.side_effect = [enrollment, None]
        with pytest.raises(UserFacingError):
            access.enqueue_academic_notification(db, principal, **args)
        enqueue.assert_not_called()
        record.assert_not_called()
        if case == "denied":
            db.get.assert_not_called()


@pytest.mark.parametrize("status", ["pending", "cancelled", "sending", "sent", "failed", "uncertain", None])
def test_cancel_notification_state_boundary(status):
    db, principal, enrollment, _, _ = setup()
    message_id = uuid4()
    item = SimpleNamespace(status=status) if status is not None else None
    db.scalars.return_value.one_or_none.return_value = item
    with patch.object(access, "require_cohort") as require, patch.object(access.audit, "record") as record:
        if status in {"pending", "cancelled"}:
            access.cancel_notification(db, principal, cohort_id=enrollment.cohort_id, message_id=message_id)
            assert item.status == "cancelled"
        else:
            with pytest.raises(UserFacingError):
                access.cancel_notification(db, principal, cohort_id=enrollment.cohort_id, message_id=message_id)
            if item is not None:
                assert item.status == status
        require.assert_called_once_with(db, principal, "email.send", enrollment.cohort_id)
        assert record.call_count == (1 if status == "pending" else 0)
        assert db.flush.call_count == (1 if status == "pending" else 0)
    db.commit.assert_not_called()
