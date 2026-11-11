from sqlalchemy.orm import Session

from app.core.authz import Principal
from app.modules.audit.models import AuditEvent


def record(db: Session, actor: Principal | None, action: str, target_type: str, target_id: str | None, **meta) -> None:
    """Adds an audit row to the current transaction. Never pass names, emails, free text or secrets in `meta`."""
    db.add(
        AuditEvent(
            actor_user_id=actor.user.id if actor else None,
            actor_roles=",".join(actor.roles) if actor else "",
            action=action,
            target_type=target_type,
            target_id=target_id,
            meta=meta,
        )
    )
