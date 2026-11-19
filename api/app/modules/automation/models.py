"""Immutable records of evaluations, not delivery receipts or completed administrative work."""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, utcnow


class AutomationExecution(Base):
    __tablename__ = "automation_execution"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_automation_execution_key"),
        CheckConstraint("kind = 'requirement_prefilter'", name="ck_automation_execution_kind"),
        CheckConstraint("outcome IN ('human_review', 'no_action')", name="ck_automation_execution_outcome"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("application.id"), index=True)
    call_id: Mapped[str] = mapped_column(ForeignKey("call.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    rule_version: Mapped[str] = mapped_column(String(40))
    idempotency_key: Mapped[str] = mapped_column(String(64))
    outcome: Mapped[str] = mapped_column(String(20))
    stage_at_evaluation: Mapped[str] = mapped_column(String(40))
    snapshot: Mapped[dict] = mapped_column(JSONB)
    recorded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
