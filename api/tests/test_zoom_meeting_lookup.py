from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.errors import UserFacingError
from app.modules.zoom import router


@pytest.mark.parametrize("case", ["disabled", "missing", "denied"])
def test_meeting_lookup_rejects_unauthorized_access(case):
    db = MagicMock()
    principal = MagicMock()
    session_id = uuid4()
    db.get.return_value = None if case == "missing" else SimpleNamespace(cohort_id="synthetic")
    with (
        patch.object(router, "settings", SimpleNamespace(zoom_enabled=case != "disabled")),
        patch.object(router, "require_cohort") as require,
    ):
        if case == "denied":
            require.side_effect = UserFacingError(403, "forbidden", "Forbidden")
        with pytest.raises(UserFacingError):
            router.get_meeting(session_id, principal, db)
        assert db.get.call_count == (0 if case == "disabled" else 1)
        if case == "denied":
            require.assert_called_once_with(db, principal, "attendance.record", "synthetic")
        else:
            require.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.parametrize("exists", [False, True])
def test_meeting_lookup_returns_only_safe_metadata(exists):
    db = MagicMock()
    principal = MagicMock()
    session_id = uuid4()
    row = SimpleNamespace(
        session_id=session_id, provider_id="123", start_at=datetime(2027, 1, 1, tzinfo=timezone.utc),
        duration_minutes=60, authentication_mode="authenticated",
        join_url="https://example.invalid/private", host_id="private",
    )
    db.get.side_effect = [SimpleNamespace(cohort_id="synthetic"), row if exists else None]
    with (
        patch.object(router, "settings", SimpleNamespace(zoom_enabled=True)),
        patch.object(router, "require_cohort") as require,
        patch.object(router, "ZoomClient") as client,
    ):
        result = router.get_meeting(session_id, principal, db)
        require.assert_called_once_with(db, principal, "attendance.record", "synthetic")
        client.assert_not_called()
    if exists:
        assert result.provider_id == "123"
        assert set(result.model_dump()) == {
            "session_id", "provider_id", "start_at", "duration_minutes", "authentication_mode",
        }
    else:
        assert result is None
    db.commit.assert_not_called()
    db.add.assert_not_called()
