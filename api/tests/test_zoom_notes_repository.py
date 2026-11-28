from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.modules.zoom.ai_schemas import MeetingNotesDraft
from app.modules.zoom.notes_repository import edit_latest


def draft(start=0, end=10, text="Synthetic notes"):
    return MeetingNotesDraft(summary=[{
        "text": text, "evidence": [{"start_seconds": start, "end_seconds": end}],
    }])


def database(version=1, enabled=True):
    db = MagicMock()
    meeting = SimpleNamespace(ai_settings={
        "cloud_recording": enabled, "transcription": enabled, "notes": enabled,
    })
    previous = SimpleNamespace(body=draft().model_dump(mode="json"), transcript_sha256="a" * 64)
    db.execute.return_value.scalar_one_or_none.return_value = meeting
    db.execute.return_value.scalar_one.return_value = previous
    db.scalar.return_value = version
    return db


def test_edit_creates_unapproved_version():
    db = database()
    actor, session = uuid4(), uuid4()
    edited = draft(text="Teacher revision")
    row = edit_latest(db, session_id=session, actor_id=actor, draft=edited, expected_version=1)
    assert row.version == 2
    assert row.created_by == actor
    assert row.session_id == session
    assert row.body == edited.model_dump(mode="json")
    assert row.transcript_sha256 == "a" * 64
    assert row.approved_at is None
    db.add.assert_called_once_with(row)
    db.flush.assert_called_once()
    db.commit.assert_not_called()


@pytest.mark.parametrize("version", [0, 2])
def test_stale_edit_rejected(version):
    db = database(version=version)
    with pytest.raises(ValueError, match="version conflict"):
        edit_latest(db, session_id=uuid4(), actor_id=uuid4(), draft=draft(), expected_version=1)
    db.add.assert_not_called()


def test_unknown_evidence_rejected():
    db = database()
    with pytest.raises(ValueError, match="Unknown evidence"):
        edit_latest(db, session_id=uuid4(), actor_id=uuid4(), draft=draft(end=20), expected_version=1)
    db.add.assert_not_called()


def test_disabled_notes_rejected():
    db = database(enabled=False)
    with pytest.raises(ValueError, match="disabled"):
        edit_latest(db, session_id=uuid4(), actor_id=uuid4(), draft=draft(), expected_version=1)
    db.add.assert_not_called()


def test_disabled_action_items_rejected():
    db = database()
    edited = MeetingNotesDraft(summary=[], action_items=[{
        "text": "Synthetic task", "evidence": [{"start_seconds": 0, "end_seconds": 10}],
    }])
    with pytest.raises(ValueError, match="Action items disabled"):
        edit_latest(db, session_id=uuid4(), actor_id=uuid4(), draft=edited, expected_version=1)
    db.add.assert_not_called()
