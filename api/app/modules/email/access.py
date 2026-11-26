"""Scoped notification creation; no arbitrary recipient addresses."""
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import audit
from app.core.authz import Principal
from app.core.errors import UserFacingError
from app.modules.email.models import EmailOutbox
from app.modules.email.service import enqueue
from app.modules.email.templates import academic_notification
from app.modules.identity.models import Person
from app.modules.learning.access import require_cohort
from app.modules.learning.models import Enrollment

EMAIL_SEND_PERMISSION = "email.send"


def enqueue_academic_notification(
    db: Session, principal: Principal, *, cohort_id: str, enrollment_id: UUID,
    idempotency_key: str, topic: str, available_at: datetime,
) -> UUID:
    require_cohort(db, principal, EMAIL_SEND_PERMISSION, cohort_id)
    enrollment = db.get(Enrollment, enrollment_id)
    if enrollment is None or enrollment.cohort_id != cohort_id or enrollment.estado != "activa":
        raise UserFacingError(404, "enrollment_not_found", "No encontramos una matrícula activa en esta cohorte.")
    person = db.get(Person, enrollment.person_id)
    if person is None:
        raise UserFacingError(404, "recipient_not_found", "No encontramos el destinatario.")
    message_id = enqueue(
        db, idempotency_key=idempotency_key, cohort_id=cohort_id,
        created_by=principal.user.id, recipient=person.email,
        rendered=academic_notification(topic=topic), available_at=available_at,
    )
    audit.record(db, principal, "email.enqueue_requested", "email_outbox", str(message_id),
                 cohort_id=cohort_id)
    return message_id


@dataclass(frozen=True)
class NotificationHistoryItem:
    message_id: UUID
    status: str
    attempts: int
    created_at: datetime
    available_at: datetime
    sent_at: datetime | None


def list_notification_history(
    db: Session, principal: Principal, *, cohort_id: str, limit: int = 50,
) -> list[NotificationHistoryItem]:
    """Return delivery metadata for the caller's own requests in an authorized cohort."""
    require_cohort(db, principal, EMAIL_SEND_PERMISSION, cohort_id)
    if not 1 <= limit <= 100:
        raise ValueError("Invalid history limit")
    statement = (
        select(EmailOutbox.id, EmailOutbox.status, EmailOutbox.attempts,
               EmailOutbox.created_at, EmailOutbox.available_at, EmailOutbox.sent_at)
        .where(EmailOutbox.cohort_id == cohort_id,
               EmailOutbox.created_by == principal.user.id)
        .order_by(EmailOutbox.created_at.desc(), EmailOutbox.id.desc())
        .limit(limit)
    )
    return [NotificationHistoryItem(*row) for row in db.execute(statement)]
