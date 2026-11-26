"""Queue state transitions. Callers own transactions and must commit claims before SMTP."""
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.email.models import EmailOutbox


def claim_next(db: Session, *, now: datetime) -> EmailOutbox | None:
    if now.utcoffset() is None:
        raise ValueError("Timezone-aware timestamp required")
    statement = (
        select(EmailOutbox)
        .where(EmailOutbox.status == "pending", EmailOutbox.available_at <= now)
        .order_by(EmailOutbox.available_at, EmailOutbox.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    item = db.scalars(statement).first()
    if item is not None:
        item.status = "sending"
        item.attempts += 1
        item.claimed_at = now
        item.error_code = None
        db.flush()
    return item


def finish_claim(
    db: Session, *, message_id: UUID, attempt: int, outcome: str, now: datetime
) -> None:
    if outcome not in ("sent", "failed", "uncertain"):
        raise ValueError("Invalid delivery outcome")
    if now.utcoffset() is None:
        raise ValueError("Timezone-aware timestamp required")
    item = db.scalars(
        select(EmailOutbox).where(EmailOutbox.id == message_id).with_for_update()
    ).one()
    if item.status != "sending" or item.attempts != attempt:
        raise ValueError("Stale delivery claim")
    item.status = outcome
    item.sent_at = now if outcome == "sent" else None
    item.error_code = {"sent": None, "failed": "delivery_failed", "uncertain": "delivery_unknown"}[outcome]
    db.flush()
