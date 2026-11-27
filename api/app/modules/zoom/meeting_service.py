"""Durable, auditable provisioning for institutional Zoom meetings."""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import audit
from app.core.authz import Principal, Scope
from app.core.db import utcnow
from app.core.errors import UserFacingError
from app.modules.attendance.models import AttendanceSession
from app.modules.learning.access import require_cohort
from app.modules.zoom.ai_schemas import SessionAISettings
from app.modules.zoom.client import AuthenticationMode, ZoomClient, ZoomError, meeting_settings
from app.modules.zoom.models import ZoomMeeting, ZoomProvisioningIntent


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
        or not host_id.strip() or host_id.strip().lower() == "me" or len(host_id) > 255
        or (profile_id is not None and len(profile_id) > 255)
        or (mode != "institutional" and profile_id is not None)
    ):
        raise ValueError("Invalid meeting parameters")
    meeting_settings(mode, profile_id)
    # Serialize provisioning for the same academic session.
    lock_session(db, session_id)
    if db.get(ZoomMeeting, session_id) is not None:
        raise UserFacingError(409, "zoom_meeting_exists", "La sesión ya tiene una reunión Zoom.")
    if db.get(ZoomProvisioningIntent, session_id) is not None:
        raise UserFacingError(409, "zoom_provisioning_unresolved", "La solicitud anterior requiere conciliación.")
    actor_id = principal.user.id
    intent = ZoomProvisioningIntent(
        session_id=session_id, operation_id=uuid4(), state="pending", host_id=host_id,
        start_at=start_at, duration_minutes=duration_minutes, authentication_mode=mode,
        profile_id=profile_id, created_by=actor_id, updated_by=actor_id,
    )
    db.add(intent)
    record_state(db, principal, intent, "pending")
    operation_id = intent.operation_id
    db.commit()

    try:
        result = client.create_meeting(
            topic, start_at.isoformat(), duration_minutes, mode, profile_id,
            host_id=host_id, operation_id=operation_id,
        )
    except ZoomError:
        lock_session(db, session_id)
        db.refresh(intent)
        if intent.state == "pending":
            record_state(db, principal, intent, "uncertain")
        db.commit()
        raise

    lock_session(db, session_id)
    db.refresh(intent)
    existing = db.get(ZoomMeeting, session_id)
    row = existing if existing is not None else confirm_meeting(db, principal, intent, result)
    db.commit()
    return row


def lock_session(db: Session, session_id: UUID) -> None:
    db.execute(select(AttendanceSession).where(
        AttendanceSession.id == session_id,
    ).with_for_update()).scalar_one()


def record_state(db: Session, actor: Principal, intent: ZoomProvisioningIntent, state: str) -> None:
    intent.state = state
    intent.updated_by = actor.user.id
    intent.updated_at = utcnow()
    audit.record(db, actor, f"zoom.provisioning_{state}", "attendance_session", str(intent.session_id),
                 operation_id=str(intent.operation_id))


def confirm_meeting(
    db: Session, actor: Principal, intent: ZoomProvisioningIntent, result: dict[str, str],
) -> ZoomMeeting:
    row = ZoomMeeting(
        session_id=intent.session_id, provider_id=result["id"], join_url=result["join_url"],
        host_id=intent.host_id, start_at=intent.start_at, duration_minutes=intent.duration_minutes,
        authentication_mode=intent.authentication_mode, profile_id=intent.profile_id,
        ai_settings=SessionAISettings().model_dump(mode="json"), created_by=intent.created_by,
    )
    db.add(row)
    record_state(db, actor, intent, "confirmed")
    return row


def reconcile_meeting(
    db: Session, principal: Principal, client: ZoomClient, *,
    session_id: UUID, operation_id: UUID, provider_id: str,
) -> ZoomMeeting:
    principal.require("staff.manage", Scope())
    session = db.get(AttendanceSession, session_id)
    if session is None:
        raise UserFacingError(404, "session_not_found", "Sesión no encontrada.")
    require_cohort(db, principal, "attendance.record", session.cohort_id)
    lock_session(db, session_id)
    intent = db.get(ZoomProvisioningIntent, session_id)
    if intent is None or intent.operation_id != operation_id:
        raise UserFacingError(409, "zoom_operation_changed", "La referencia no corresponde a esta sesión.")
    existing = db.get(ZoomMeeting, session_id)
    if existing is not None:
        if existing.provider_id != provider_id:
            raise UserFacingError(409, "zoom_meeting_exists", "La sesión ya tiene otra reunión confirmada.")
        return existing
    result = client.recover_meeting(provider_id, operation_id, intent.host_id,
                                    intent.start_at, intent.duration_minutes)
    row = confirm_meeting(db, principal, intent, result)
    db.commit()
    return row


def provision_institutional_meeting(
    db: Session, principal: Principal, client: ZoomClient, *, session_id: UUID,
    topic: str, start_at: datetime, duration_minutes: int, mode: AuthenticationMode,
) -> ZoomMeeting:
    """Public-facing service boundary: host and profile are exclusively server configured."""
    config = client.config
    if not config.zoom_enabled or not config.zoom_provisioning_enabled or not config.zoom_host_id:
        raise UserFacingError(404, "zoom_disabled", "Creación de reuniones no disponible.")
    profile_id = config.zoom_institutional_profile_id if mode == "institutional" else None
    if mode == "institutional" and not profile_id:
        raise UserFacingError(409, "zoom_profile_unavailable", "Perfil institucional no configurado.")
    return provision_meeting(
        db, principal, client, session_id=session_id, topic=topic,
        start_at=start_at, duration_minutes=duration_minutes,
        host_id=config.zoom_host_id, mode=mode, profile_id=profile_id,
    )
