"""Update-protected evaluation evidence; authorized application deletion cascades to its records."""
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
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("application.id", ondelete="CASCADE"), index=True)
    call_id: Mapped[str] = mapped_column(ForeignKey("call.id"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    rule_version: Mapped[str] = mapped_column(String(40))
    idempotency_key: Mapped[str] = mapped_column(String(64))
    outcome: Mapped[str] = mapped_column(String(20))
    stage_at_evaluation: Mapped[str] = mapped_column(String(40))
    snapshot: Mapped[dict] = mapped_column(JSONB)
    recorded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SimulatedReminder(Base):
    """Staff-requested simulation, never a delivery receipt or completion claim."""
    __tablename__ = "simulated_reminder"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_simulated_reminder_key"),
        CheckConstraint("kind IN ('documentation', 'exercises')", name="ck_simulated_reminder_kind"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("application.id", ondelete="CASCADE"), index=True)
    call_id: Mapped[str] = mapped_column(ForeignKey("call.id"))
    task_ref: Mapped[str] = mapped_column(String(80))
    kind: Mapped[str] = mapped_column(String(40))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    rule_version: Mapped[str] = mapped_column(String(40))
    idempotency_key: Mapped[str] = mapped_column(String(64))
    recorded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    simulated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
