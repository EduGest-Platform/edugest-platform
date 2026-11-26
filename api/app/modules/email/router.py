"""Authenticated notification requests; delivery remains asynchronous."""
from uuid import UUID

from fastapi import APIRouter
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field

from app.core.config import settings
from app.core.deps import CurrentPrincipal, DB
from app.core.errors import UserFacingError
from app.modules.email.access import enqueue_academic_notification

router = APIRouter(tags=["email"])


class AcademicNotificationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enrollment_id: UUID
    idempotency_key: str = Field(min_length=1, max_length=128)
    topic: str = Field(min_length=1, max_length=120)
    available_at: AwareDatetime


class NotificationAcceptedOut(BaseModel):
    message_id: UUID


@router.post("/cohorts/{cohort_id}/email/notifications",
             response_model=NotificationAcceptedOut, status_code=202)
def request_academic_notification(
    cohort_id: str, body: AcademicNotificationIn, p: CurrentPrincipal, db: DB,
):
    if not settings.email_enabled:
        raise UserFacingError(404, "email_disabled", "Integración no disponible.")
    try:
        message_id = enqueue_academic_notification(
            db, p, cohort_id=cohort_id, enrollment_id=body.enrollment_id,
            idempotency_key=body.idempotency_key, topic=body.topic,
            available_at=body.available_at,
        )
        db.commit()
    except ValueError:
        db.rollback()
        raise UserFacingError(422, "email_invalid_request",
                              "Solicitud de notificación no válida.") from None
    return NotificationAcceptedOut(message_id=message_id)
