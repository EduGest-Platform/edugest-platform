"""Staff-only review API; no learner publication or external generation."""
import uuid
from datetime import datetime

import httpx
from fastapi import APIRouter
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.core.config import settings
from app.core.deps import CurrentPrincipal, DB
from app.core.errors import UserFacingError
from app.modules.attendance.models import AttendanceSession
from app.modules.learning.access import require_cohort
from app.modules.zoom.ai_schemas import MeetingNotesDraft, SessionAISettings
from app.modules.zoom.client import AuthenticationMode, ZoomClient, ZoomError
from app.modules.zoom.meeting_service import provision_institutional_meeting
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


class MeetingCreateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    topic: str = Field(min_length=1, max_length=200)
    start_at: AwareDatetime
    duration_minutes: int = Field(ge=1, le=1440)
    authentication_mode: AuthenticationMode = "authenticated"


class MeetingOut(BaseModel):
    session_id: uuid.UUID
    provider_id: str
    start_at: datetime
    duration_minutes: int
    authentication_mode: AuthenticationMode


@router.post("/attendance-sessions/{session_id}/zoom/meeting", response_model=MeetingOut, status_code=201)
def create_meeting(session_id: uuid.UUID, body: MeetingCreateIn, p: CurrentPrincipal, db: DB):
    try:
        with httpx.Client() as transport:
            row = provision_institutional_meeting(
                db, p, ZoomClient(settings, transport), session_id=session_id,
                topic=body.topic, start_at=body.start_at, duration_minutes=body.duration_minutes,
                mode=body.authentication_mode,
            )
        result = MeetingOut(
            session_id=row.session_id, provider_id=row.provider_id, start_at=row.start_at,
            duration_minutes=row.duration_minutes, authentication_mode=row.authentication_mode,
        )
        db.commit()
    except ZoomError:
        db.rollback()
        raise UserFacingError(502, "zoom_provider_error", "No se pudo confirmar la reunión. Requiere revisión antes de reintentar.") from None
    except ValueError:
        db.rollback()
        raise UserFacingError(422, "zoom_invalid_meeting", "Configuración de reunión no válida.") from None
    return result
