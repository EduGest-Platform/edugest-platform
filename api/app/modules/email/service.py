"""Internal enqueue primitive; caller must authorize cohort, actor and recipient."""
from datetime import datetime
from email.headerregistry import Address
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.db import utcnow
from app.modules.email.models import EmailOutbox
from app.modules.email.templates import RenderedEmail


def enqueue(
    db: Session, *, idempotency_key: str, cohort_id: str, created_by: UUID,
    recipient: str, rendered: RenderedEmail, available_at: datetime,
) -> UUID:
    """Persist a trusted rendered message; caller owns transaction and authorization."""
    if not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValueError("Invalid idempotency key")
    if available_at.utcoffset() is None:
        raise ValueError("Timezone-aware schedule required")
    if len(recipient) > 320 or any(c in recipient for c in "\r\n"):
        raise ValueError("Invalid recipient")
    address = Address(addr_spec=recipient)
    if not address.username or not address.domain:
        raise ValueError("Invalid recipient")
    if not rendered.subject.strip() or len(rendered.subject) > 200 or any(c in rendered.subject for c in "\r\n"):
        raise ValueError("Invalid subject")
    if any(not body.strip() or len(body.encode("utf-8")) > 100000 for body in (rendered.text, rendered.html)):
        raise ValueError("Invalid message body")
    values = dict(
        idempotency_key=idempotency_key, cohort_id=cohort_id, created_by=created_by,
        recipient=recipient, subject=rendered.subject, text_body=rendered.text,
        html_body=rendered.html, available_at=available_at,
    )
    statement = (
        insert(EmailOutbox)
        .values(**values, id=uuid4(), status="pending", attempts=0, created_at=utcnow())
        .on_conflict_do_nothing(index_elements=[EmailOutbox.idempotency_key])
        .returning(EmailOutbox.id)
    )
    inserted = db.execute(statement).scalar_one_or_none()
    if inserted is not None:
        return inserted
    existing = db.scalars(
        select(EmailOutbox).where(EmailOutbox.idempotency_key == idempotency_key)
    ).one()
    if any(getattr(existing, key) != value for key, value in values.items()):
        raise ValueError("Idempotency key conflict")
    return existing.id
