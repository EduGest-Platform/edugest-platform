from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.modules.email import worker
from app.modules.email.transport import DeliveryError, TransientPreSendError


@pytest.mark.parametrize(
    "error,outcome,retry",
    [
        (None, "sent", False),
        (ValueError("invalid"), "failed", False),
        (DeliveryError("unknown"), "uncertain", False),
        (TransientPreSendError("temporary"), "transient_pre_send", True),
    ],
)
def test_worker_outcomes(error, outcome, retry):
    item = SimpleNamespace(
        id=uuid4(), attempts=1, recipient="student@example.test",
        subject="Test", text_body="Synthetic", html_body=None,
    )
    with (
        patch.object(worker, "SessionLocal") as sessions,
        patch.object(worker, "claim_next", return_value=item),
        patch.object(worker, "finish_claim") as finish,
        patch.object(worker, "schedule_retry") as schedule,
        patch.object(worker, "send_email") as send,
    ):
        claim_tx, result_tx = MagicMock(), MagicMock()
        sessions.begin.side_effect = [claim_tx, result_tx]

        def deliver(*args, **kwargs):
            claim_tx.__exit__.assert_called_once_with(None, None, None)
            result_tx.__enter__.assert_not_called()
            if error is not None:
                raise error

        send.side_effect = deliver
        assert worker.process_one(SimpleNamespace(email_enabled=True))
        assert finish.call_args.kwargs["outcome"] == outcome
        assert finish.call_args.kwargs["message_id"] == item.id
        assert finish.call_args.kwargs["attempt"] == 1
        assert schedule.called == retry
        result_tx.__exit__.assert_called_once_with(None, None, None)


def test_disabled_worker_never_claims():
    with patch.object(worker, "SessionLocal") as sessions:
        assert not worker.process_one(SimpleNamespace(email_enabled=False))
        sessions.begin.assert_not_called()


def test_empty_queue_never_sends():
    with (
        patch.object(worker, "SessionLocal"),
        patch.object(worker, "claim_next", return_value=None),
        patch.object(worker, "send_email") as send,
    ):
        assert not worker.process_one(SimpleNamespace(email_enabled=True))
        send.assert_not_called()


def test_claim_commit_failure_never_sends():
    item = SimpleNamespace(
        id=uuid4(), attempts=1, recipient="student@example.test",
        subject="Test", text_body="Synthetic", html_body=None,
    )
    with (
        patch.object(worker, "SessionLocal") as sessions,
        patch.object(worker, "claim_next", return_value=item),
        patch.object(worker, "send_email") as send,
        patch.object(worker, "finish_claim") as finish,
    ):
        sessions.begin.return_value.__exit__.side_effect = RuntimeError("commit failed")
        with pytest.raises(RuntimeError, match="commit failed"):
            worker.process_one(SimpleNamespace(email_enabled=True))
        send.assert_not_called()
        finish.assert_not_called()
        sessions.begin.assert_called_once_with()


def test_result_commit_failure_does_not_resend():
    item = SimpleNamespace(
        id=uuid4(), attempts=1, recipient="student@example.test",
        subject="Test", text_body="Synthetic", html_body=None,
    )
    with (
        patch.object(worker, "SessionLocal") as sessions,
        patch.object(worker, "claim_next", return_value=item),
        patch.object(worker, "send_email") as send,
        patch.object(worker, "finish_claim"),
        patch.object(worker, "schedule_retry") as retry,
    ):
        claim_tx, result_tx = MagicMock(), MagicMock()
        sessions.begin.side_effect = [claim_tx, result_tx]
        result_tx.__exit__.side_effect = RuntimeError("result commit failed")
        with pytest.raises(RuntimeError, match="result commit failed"):
            worker.process_one(SimpleNamespace(email_enabled=True))
        send.assert_called_once()
        retry.assert_not_called()
