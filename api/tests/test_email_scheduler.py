from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.modules.email import scheduler

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def config(enabled=True, timeout=15):
    return SimpleNamespace(email_enabled=enabled, email_timeout_seconds=timeout)


def test_disabled_cycle_does_not_access_database():
    with patch.object(scheduler, "SessionLocal") as sessions:
        assert scheduler.run_cycle(config(False)) == 0
        sessions.begin.assert_not_called()


@pytest.mark.parametrize("size", [0, -1, 101])
def test_invalid_batch_size(size):
    with pytest.raises(ValueError, match="batch size"):
        scheduler.run_cycle(config(), batch_size=size)


@pytest.mark.parametrize("timeout,window", [(15, 3600), (200, 4000)])
def test_recovery_commits_before_processing(timeout, window):
    with (
        patch.object(scheduler, "SessionLocal") as sessions,
        patch.object(scheduler, "utcnow", return_value=NOW),
        patch.object(scheduler, "recover_interrupted") as recover,
        patch.object(scheduler, "process_one") as process,
    ):
        tx = sessions.begin.return_value

        def deliver(settings):
            tx.__exit__.assert_called_once_with(None, None, None)
            return True

        process.side_effect = deliver
        assert scheduler.run_cycle(config(timeout=timeout), batch_size=2) == 2
        recover.assert_called_once_with(
            tx.__enter__.return_value, cutoff=NOW - timedelta(seconds=window), limit=2
        )
        assert process.call_count == 2


def test_cycle_stops_when_queue_empty():
    with (
        patch.object(scheduler, "SessionLocal"),
        patch.object(scheduler, "recover_interrupted"),
        patch.object(scheduler, "process_one", side_effect=[True, False]) as process,
    ):
        assert scheduler.run_cycle(config()) == 1
        assert process.call_count == 2


def test_disabled_main_does_not_start_loop():
    with (
        patch.object(scheduler, "settings", config(False)),
        patch.object(scheduler, "Event") as event,
    ):
        scheduler.main()
        event.assert_not_called()
