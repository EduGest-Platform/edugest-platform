import uuid
from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, utcnow
from app.modules.admissions.models import STAGES

# Human decisions that end pre-selection (or postpone a silence review). The platform never takes them by itself.
DECISIONS = ("convocada", "retirada_expresa", "silencio_confirmado", "silencio_reprogramado")


class PreselectionDecision(Base):
    """Append-only record of who decided what about the end of pre-selection, why, and on which evidence."""

    __tablename__ = "preselection_decision"
    __table_args__ = (
        CheckConstraint(f"decision IN {DECISIONS}", name="ck_preselection_decision_decision"),
        CheckConstraint(f"from_stage IN {STAGES} AND to_stage IN {STAGES}", name="ck_preselection_decision_stages"),
        CheckConstraint("length(btrim(reason)) > 0", name="ck_preselection_decision_reason"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("application.id", ondelete="CASCADE"), index=True)
    decision: Mapped[str] = mapped_column(String(30))
    from_stage: Mapped[str] = mapped_column(String(40))
    to_stage: Mapped[str] = mapped_column(String(40))
    reason: Mapped[str] = mapped_column(String(500))
    actor_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    # Contact evidence and the silence policy as they were when the decision was taken, so later policy edits do not rewrite history.
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
