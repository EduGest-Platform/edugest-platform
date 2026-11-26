"""Staff-only review API; no learner publication or external generation."""
import uuid
from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.config import settings
from app.core.deps import CurrentPrincipal, DB
from app.core.errors import UserFacingError
from app.modules.attendance.models import AttendanceSession
from app.modules.learning.access import require_cohort
from app.modules.zoom.ai_schemas import MeetingNotesDraft, SessionAISettings
from app.modules.zoom.models import ZoomMeeting, ZoomNotesVersion
from app.modules.zoom.notes_repository import approve_latest, edit_latest

router = APIRouter(tags=["zoom"])


class NotesOut(BaseModel):
    version: int
    body: MeetingNotesDraft
    created_at: datetime
    approved_at: datetime | None


class ApprovalIn(BaseModel):
    expected_version: int = Field(ge=1)


def _access(db: DB, p: CurrentPrincipal, session_id: uuid.UUID):
    if not settings.zoom_enabled:
        raise UserFacingError(404, "zoom_disabled", "Integración no disponible.")
    session = db.get(AttendanceSession, session_id)
    if session is None:
        raise UserFacingError(404, "session_not_found", "Sesión no encontrada.")
    require_cohort(db, p, "attendance.record", session.cohort_id)
    meeting = db.get(ZoomMeeting, session_id)
    if meeting is None or not SessionAISettings.model_validate(meeting.ai_settings).notes:
        raise UserFacingError(404, "notes_unavailable", "Notas no disponibles.")


def _out(row: ZoomNotesVersion) -> NotesOut:
    return NotesOut(version=row.version, body=MeetingNotesDraft.model_validate(row.body),
                    created_at=row.created_at, approved_at=row.approved_at)


@router.get("/attendance-sessions/{session_id}/zoom/notes", response_model=list[NotesOut])
def list_notes(session_id: uuid.UUID, p: CurrentPrincipal, db: DB):
    _access(db, p, session_id)
    rows = db.scalars(select(ZoomNotesVersion).where(
        ZoomNotesVersion.session_id == session_id
    ).order_by(ZoomNotesVersion.version.desc()).limit(50))
    return [_out(row) for row in rows]


@router.post("/attendance-sessions/{session_id}/zoom/notes/approve", response_model=NotesOut)
def approve_notes(session_id: uuid.UUID, body: ApprovalIn, p: CurrentPrincipal, db: DB):
    _access(db, p, session_id)
    try:
        row = approve_latest(db, session_id=session_id, actor_id=p.user.id,
                             expected_version=body.expected_version)
    except ValueError:
        db.rollback()
        raise UserFacingError(409, "notes_conflict", "Las notas han cambiado o no están disponibles.") from None
    result = _out(row)
    db.commit()
    return result


class EditNotesIn(BaseModel):
    expected_version: int = Field(ge=1)
    draft: MeetingNotesDraft


@router.post("/attendance-sessions/{session_id}/zoom/notes/edit", response_model=NotesOut)
def edit_notes(session_id: uuid.UUID, body: EditNotesIn, p: CurrentPrincipal, db: DB):
    _access(db, p, session_id)
    try:
        row = edit_latest(db, session_id=session_id, actor_id=p.user.id,
                          draft=body.draft, expected_version=body.expected_version)
    except ValueError:
        db.rollback()
        raise UserFacingError(409, "notes_conflict", "Las notas han cambiado o la edición no es válida.") from None
    result = _out(row)
    db.commit()
    return result
