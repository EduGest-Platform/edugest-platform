"""Process one queued email; scheduling and authorization are external responsibilities."""
from app.core.config import Settings
from app.core.db import SessionLocal, utcnow
from app.modules.email.queue import claim_next, finish_claim, schedule_retry
from app.modules.email.transport import DeliveryError, TransientPreSendError, send_email


def process_one(config: Settings) -> bool:
    """Return whether a message was claimed, not whether delivery succeeded."""
    if not config.email_enabled:
        return False

    # Release the row lock before any network I/O; never send an uncommitted claim.
    with SessionLocal.begin() as db:
        item = claim_next(db, now=utcnow())
        if item is None:
            return False
        message_id, attempt = item.id, item.attempts
        payload = {
            "recipient": item.recipient,
            "subject": item.subject,
            "body": item.text_body,
            "html_body": item.html_body,
        }

    try:
        send_email(config, **payload)
    except TransientPreSendError:
        outcome = "transient_pre_send"
    except ValueError:
        outcome = "failed"
    except DeliveryError:
        # The transport cannot prove whether the remote server accepted the message.
        outcome = "uncertain"
    else:
        outcome = "sent"

    with SessionLocal.begin() as db:
        now = utcnow()
        finish_claim(db, message_id=message_id, attempt=attempt, outcome=outcome, now=now)
        if outcome == "transient_pre_send":
            schedule_retry(db, message_id=message_id, now=now)
    return True
