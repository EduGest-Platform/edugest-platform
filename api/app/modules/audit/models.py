import uuid
from datetime import datetime

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, utcnow


class AuditEvent(Base):
    """Append-only (enforced by a DB trigger). Metadata carries IDs and codes, never personal data or secrets."""

    __tablename__ = "audit_event"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    actor_roles: Mapped[str] = mapped_column(String(200), default="")
    action: Mapped[str] = mapped_column(String(60), index=True)
    target_type: Mapped[str] = mapped_column(String(40))
    target_id: Mapped[str | None] = mapped_column(String(60))
    meta: Mapped[dict] = mapped_column(JSON, default=dict)
