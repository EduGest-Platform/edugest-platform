from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.errors import UserFacingError
from app.modules.zoom import meeting_service
from app.modules.zoom.client import ZoomError


def setup():
    db, client = MagicMock(), MagicMock()
    session = SimpleNamespace(cohort_id="synthetic-cohort")
    db.get.side_effect = [session, None]
    client.config.zoom_enabled = True
    client.create_meeting.return_value = {"id": "123456789", "join_url": "https://zoom.us/j/123456789"}
    principal = SimpleNamespace(user=SimpleNamespace(id=uuid4()))
    args = dict(session_id=uuid4(), topic="Synthetic class",
                start_at=datetime(2027, 1, 1, tzinfo=timezone.utc),
                duration_minutes=60, host_id="synthetic-host", mode="authenticated")
    return db, client, principal, args


def test_provision_persists_link_without_enabling_ai():
    db, client, principal, args = setup()
    with patch.object(meeting_service, "require_cohort") as require:
        row = meeting_service.provision_meeting(db, principal, client, **args)
    require.assert_called_once_with(db, principal, "attendance.record", "synthetic-cohort")
    assert row.session_id == args["session_id"]
    assert row.provider_id == "123456789"
    assert row.created_by == principal.user.id
    assert row.ai_settings["notes"] is False
    assert row.ai_settings["cloud_recording"] is False
    db.add.assert_called_once_with(row)
    db.flush.assert_called_once()
    db.commit.assert_not_called()


@pytest.mark.parametrize("case", ["denied", "duplicate", "disabled", "missing"])
def test_rejected_requests_never_call_zoom(case):
    db, client, principal, args = setup()
    with patch.object(meeting_service, "require_cohort") as require:
        if case == "denied":
            require.side_effect = UserFacingError(403, "forbidden", "Forbidden")
        elif case == "duplicate":
            db.get.side_effect = [SimpleNamespace(cohort_id="synthetic-cohort"), object()]
        elif case == "disabled":
            client.config.zoom_enabled = False
        else:
            db.get.side_effect = [None]
        with pytest.raises(UserFacingError):
            meeting_service.provision_meeting(db, principal, client, **args)
    client.create_meeting.assert_not_called()
    db.add.assert_not_called()


@pytest.mark.parametrize("changes", [
    {"duration_minutes": 0},
    {"start_at": datetime(2027, 1, 1)},
    {"mode": "institutional"},
    {"profile_id": "unexpected"},
])
def test_invalid_parameters_never_call_zoom(changes):
    db, client, principal, args = setup()
    args.update(changes)
    with patch.object(meeting_service, "require_cohort"), pytest.raises(ValueError):
        meeting_service.provision_meeting(db, principal, client, **args)
    client.create_meeting.assert_not_called()
    db.add.assert_not_called()


def test_provider_failure_does_not_persist_or_retry():
    db, client, principal, args = setup()
    client.create_meeting.side_effect = ZoomError("Unknown outcome")
    with patch.object(meeting_service, "require_cohort"), pytest.raises(ZoomError):
        meeting_service.provision_meeting(db, principal, client, **args)
    client.create_meeting.assert_called_once()
    db.add.assert_not_called()
    db.commit.assert_not_called()
