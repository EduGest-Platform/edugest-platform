"""Internal persistence helpers. Callers must enforce cohort permissions.

The caller owns the transaction; these helpers never commit or publish to RAG.
"""
import hashlib
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import utcnow
from app.modules.zoom.ai_schemas import MeetingNotesDraft, SessionAISettings
from app.modules.zoom.models import ZoomMeeting, ZoomNotesVersion


def _lock_meeting(db: Session, session_id: uuid.UUID) -> ZoomMeeting:
    meeting = db.execute(select(ZoomMeeting).where(
        ZoomMeeting.session_id == session_id
    ).with_for_update()).scalar_one_or_none()
    if meeting is None:
        raise ValueError("Meeting not found")
    if not SessionAISettings.model_validate(meeting.ai_settings).notes:
        raise ValueError("Meeting notes are disabled")
    return meeting


def _latest_version(db: Session, session_id: uuid.UUID) -> int:
    return db.scalar(select(func.max(ZoomNotesVersion.version)).where(
        ZoomNotesVersion.session_id == session_id
    )) or 0


def store_draft(db: Session, *, session_id: uuid.UUID, actor_id: uuid.UUID,
                draft: MeetingNotesDraft, transcript: bytes,
                expected_version: int) -> ZoomNotesVersion:
    _lock_meeting(db, session_id)
    current = _latest_version(db, session_id)
    if current != expected_version:
        raise ValueError("Notes version conflict")
    if not transcript:
        raise ValueError("Missing transcript")
    row = ZoomNotesVersion(session_id=session_id, version=current + 1,
                           body=draft.model_dump(mode="json"),
                           transcript_sha256=hashlib.sha256(transcript).hexdigest(),
                           created_by=actor_id)
    db.add(row)
    db.flush()
    return row


def approve_latest(db: Session, *, session_id: uuid.UUID,
                   actor_id: uuid.UUID, expected_version: int) -> ZoomNotesVersion:
    _lock_meeting(db, session_id)
    if expected_version < 1 or _latest_version(db, session_id) != expected_version:
        raise ValueError("Notes version conflict")
    row = db.execute(select(ZoomNotesVersion).where(
        ZoomNotesVersion.session_id == session_id,
        ZoomNotesVersion.version == expected_version
    ).with_for_update()).scalar_one()
    if row.approved_at is None:
        row.approved_by = actor_id
        row.approved_at = utcnow()
        db.flush()
    return row


def edit_latest(db: Session, *, session_id: uuid.UUID, actor_id: uuid.UUID,
                draft: MeetingNotesDraft, expected_version: int) -> ZoomNotesVersion:
    meeting = _lock_meeting(db, session_id)
    if expected_version < 1 or _latest_version(db, session_id) != expected_version:
        raise ValueError("Notes version conflict")
    previous = db.execute(select(ZoomNotesVersion).where(
        ZoomNotesVersion.session_id == session_id,
        ZoomNotesVersion.version == expected_version
    )).scalar_one()
    original = MeetingNotesDraft.model_validate(previous.body)
    allowed = {(span.start_seconds, span.end_seconds)
               for item in (*original.summary, *original.key_topics,
                            *original.reinforcement_topics, *original.action_items)
               for span in item.evidence}
    if draft.action_items and not SessionAISettings.model_validate(meeting.ai_settings).action_items:
        raise ValueError("Action items disabled")
    for item in (*draft.summary, *draft.key_topics, *draft.reinforcement_topics, *draft.action_items):
        if any((span.start_seconds, span.end_seconds) not in allowed for span in item.evidence):
            raise ValueError("Unknown evidence")
    row = ZoomNotesVersion(session_id=session_id, version=expected_version + 1,
                           body=draft.model_dump(mode="json"),
                           transcript_sha256=previous.transcript_sha256,
                           created_by=actor_id)
    db.add(row)
    db.flush()
    return row
