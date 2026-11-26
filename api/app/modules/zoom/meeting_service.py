"""Internal provisioning; caller owns commit and must reconcile ambiguous failures."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.authz import Principal
from app.core.errors import UserFacingError
from app.modules.attendance.models import AttendanceSession
from app.modules.learning.access import require_cohort
from app.modules.zoom.ai_schemas import SessionAISettings
from app.modules.zoom.client import AuthenticationMode, ZoomClient, meeting_settings
from app.modules.zoom.models import ZoomMeeting


def provision_meeting(
    db: Session, principal: Principal, client: ZoomClient, *, session_id: UUID,
    topic: str, start_at: datetime, duration_minutes: int, host_id: str,
    mode: AuthenticationMode, profile_id: str | None = None,
) -> ZoomMeeting:
    """Host and authentication profile must be selected from trusted institutional configuration."""
    session = db.get(AttendanceSession, session_id)
    if session is None:
        raise UserFacingError(404, "session_not_found", "Sesión no encontrada.")
    require_cohort(db, principal, "attendance.record", session.cohort_id)
    if not client.config.zoom_enabled:
        raise UserFacingError(404, "zoom_disabled", "Integración no disponible.")
    if (
        start_at.utcoffset() is None or not 1 <= duration_minutes <= 1440
        or not topic.strip() or len(topic) > 200
        or not host_id.strip() or len(host_id) > 255
        or (profile_id is not None and len(profile_id) > 255)
        or (mode != "institutional" and profile_id is not None)
    ):
        raise ValueError("Invalid meeting parameters")
    meeting_settings(mode, profile_id)
    # Serialize provisioning for the same academic session.
    db.execute(select(AttendanceSession).where(
        AttendanceSession.id == session_id
    ).with_for_update()).scalar_one()
    if db.get(ZoomMeeting, session_id) is not None:
        raise UserFacingError(409, "zoom_meeting_exists", "La sesión ya tiene una reunión Zoom.")
    result = client.create_meeting(
        topic, start_at.isoformat(), duration_minutes, mode, profile_id, host_id=host_id,
    )
    row = ZoomMeeting(
        session_id=session_id, provider_id=result["id"], join_url=result["join_url"],
        host_id=host_id, start_at=start_at, duration_minutes=duration_minutes,
        authentication_mode=mode, profile_id=profile_id,
        ai_settings=SessionAISettings().model_dump(mode="json"), created_by=principal.user.id,
    )
    db.add(row)
    db.flush()
    return row
