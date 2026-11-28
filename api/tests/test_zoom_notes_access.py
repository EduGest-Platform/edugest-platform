from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.core.errors import UserFacingError
from app.modules.zoom import router as review


@pytest.mark.parametrize("operation", ["list", "approve", "edit"])
def test_denied_cohort_cannot_access_notes(operation):
    db = MagicMock()
    db.get.return_value = SimpleNamespace(cohort_id="synthetic-cohort")
    principal = SimpleNamespace(user=SimpleNamespace(id=uuid4()))
    session_id = uuid4()
    denied = UserFacingError(403, "forbidden", "Forbidden")
    with (
        patch.object(review, "settings", SimpleNamespace(zoom_enabled=True)),
        patch.object(review, "require_cohort", side_effect=denied) as require,
        patch.object(review, "approve_latest") as approve,
        patch.object(review, "edit_latest") as edit,
    ):
        with pytest.raises(UserFacingError) as exc:
            if operation == "list":
                review.list_notes(session_id, principal, db)
            elif operation == "approve":
                review.approve_notes(session_id, review.ApprovalIn(expected_version=1), principal, db)
            else:
                body = review.EditNotesIn(expected_version=1, draft={"summary": []})
                review.edit_notes(session_id, body, principal, db)
        assert exc.value is denied
        require.assert_called_once_with(db, principal, "attendance.record", "synthetic-cohort")
        db.scalars.assert_not_called()
        db.commit.assert_not_called()
        approve.assert_not_called()
        edit.assert_not_called()


def test_disabled_integration_never_reads_session():
    db = MagicMock()
    with patch.object(review, "settings", SimpleNamespace(zoom_enabled=False)):
        with pytest.raises(UserFacingError):
            review.list_notes(uuid4(), MagicMock(), db)
    db.get.assert_not_called()


@pytest.mark.parametrize("session_exists", [False, True])
def test_unavailable_notes_never_read_versions(session_exists):
    db = MagicMock()
    db.get.side_effect = [SimpleNamespace(cohort_id="synthetic-cohort"), None] if session_exists else [None]
    with (
        patch.object(review, "settings", SimpleNamespace(zoom_enabled=True)),
        patch.object(review, "require_cohort"),
    ):
        with pytest.raises(UserFacingError):
            review.list_notes(uuid4(), MagicMock(), db)
    db.scalars.assert_not_called()
