"""KAN-247: derived delivery state must compare instants, including repeated local hours."""
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from app.modules.submissions.service import delivery_state, submission_out


def local(hour, minute, fold):
    return datetime(2026, 10, 25, hour, minute, tzinfo=ZoneInfo('Europe/Madrid'), fold=fold)


def delivery(first):
    return SimpleNamespace(id=uuid.uuid4(), assignment_id=uuid.uuid4(), enrollment_id=uuid.uuid4(), portfolio_url=None,
                           check_results=None, status='submitted', revision=1, first_submitted_at=first,
                           submitted_at=first, reviewed_at=None)


def test_repeated_local_hour_late_submission_is_not_on_time():
    assignment = SimpleNamespace(due_at=local(2, 30, 0))
    submitted = delivery(local(2, 15, 1))  # 45 elapsed minutes AFTER the deadline.
    assert delivery_state(assignment, submitted, submitted.first_submitted_at) == 'late'
    assert submission_out(submitted, assignment).late is True


def test_repeated_local_hour_does_not_mark_an_earlier_instant_late():
    assignment = SimpleNamespace(due_at=local(2, 15, 1))
    submitted = delivery(local(2, 30, 0))  # 45 elapsed minutes BEFORE the deadline.
    assert delivery_state(assignment, submitted, submitted.first_submitted_at) == 'on_time'
    assert submission_out(submitted, assignment).late is False


def test_pending_delivery_becomes_overdue_in_repeated_hour():
    assignment = SimpleNamespace(due_at=local(2, 30, 0))
    assert delivery_state(assignment, None, local(2, 15, 1)) == 'overdue'


@pytest.mark.parametrize(('delta', 'state', 'without_submission'), [(-1, 'on_time', 'pending'), (0, 'on_time', 'pending'), (1, 'late', 'overdue')])
def test_microsecond_boundary_preserves_existing_inclusive_deadline(delta, state, without_submission):
    deadline = datetime(2026, 11, 24, 12, tzinfo=timezone.utc)
    instant = deadline + timedelta(microseconds=delta)
    assignment = SimpleNamespace(due_at=deadline)
    assert delivery_state(assignment, delivery(instant), instant) == state
    assert delivery_state(assignment, None, instant) == without_submission


def test_equal_instants_with_different_offsets_are_on_time():
    deadline = datetime.fromisoformat('2026-11-24T12:00:00+00:00')
    submitted = delivery(datetime.fromisoformat('2026-11-24T13:00:00+01:00'))
    assert delivery_state(SimpleNamespace(due_at=deadline), submitted, deadline) == 'on_time'


def test_resubmission_date_does_not_replace_first_submission_date():
    deadline = datetime(2026, 11, 24, 12, tzinfo=timezone.utc)
    submitted = delivery(deadline - timedelta(minutes=1))
    submitted.submitted_at = deadline + timedelta(days=1)
    assert delivery_state(SimpleNamespace(due_at=deadline), submitted, submitted.submitted_at) == 'on_time'


@pytest.mark.parametrize('naive_target', ['deadline', 'submission', 'now'])
def test_unknown_timezone_is_rejected_instead_of_assuming_machine_timezone(naive_target):
    aware = datetime(2026, 11, 24, 12, tzinfo=timezone.utc)
    naive = aware.replace(tzinfo=None)
    assignment = SimpleNamespace(due_at=naive if naive_target == 'deadline' else aware)
    submitted = delivery(naive if naive_target == 'submission' else aware)
    with pytest.raises(ValueError, match='timezone-aware'):
        delivery_state(assignment, None if naive_target == 'now' else submitted, naive if naive_target == 'now' else aware)
