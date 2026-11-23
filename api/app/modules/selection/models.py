import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, utcnow
from app.modules.admissions.models import STAGES

# Human decisions that close selection. The platform never takes them by itself (PO 19/11/2026, KAN-48).
SELECTION_DECISIONS = ("admitida", "lista_espera", "no_admitida")


class SelectionDecision(Base):
    """Append-only record of who decided the admission of an application, why, and the enrollment it created."""

    __tablename__ = "selection_decision"
    __table_args__ = (
        CheckConstraint(f"decision IN {SELECTION_DECISIONS}", name="ck_selection_decision_decision"),
        CheckConstraint(f"from_stage IN {STAGES} AND to_stage IN {STAGES}", name="ck_selection_decision_stages"),
        CheckConstraint("length(btrim(reason)) > 0", name="ck_selection_decision_reason"),
        # Only an admission enrols: the cohort and the enrollment are recorded together, and only for «admitida».
        CheckConstraint(
            "(decision = 'admitida') = (cohort_id IS NOT NULL AND enrollment_id IS NOT NULL)",
            name="ck_selection_decision_enrollment",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("application.id", ondelete="CASCADE"), index=True)
    decision: Mapped[str] = mapped_column(String(20))
    from_stage: Mapped[str] = mapped_column(String(40))
    to_stage: Mapped[str] = mapped_column(String(40))
    reason: Mapped[str] = mapped_column(String(500))
    actor_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    cohort_id: Mapped[str | None] = mapped_column(ForeignKey("cohort.id"))
    enrollment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("enrollment.id"))


class SelectionApproval(Base):
    """One person's vote on how selection should end. When `call.selection_quorum` different people agree on the same
    decision (and cohort), the SelectionDecision is applied and the votes point to it. Pending votes have no decision_id."""

    __tablename__ = "selection_approval"
    __table_args__ = (
        CheckConstraint(f"decision IN {SELECTION_DECISIONS}", name="ck_selection_approval_decision"),
        CheckConstraint("length(btrim(reason)) > 0", name="ck_selection_approval_reason"),
        CheckConstraint("(decision = 'admitida') = (cohort_id IS NOT NULL)", name="ck_selection_approval_cohort"),
        # One pending vote per person and application: a person cannot reach the quorum alone.
        Index("uq_selection_approval_pending_actor", "application_id", "actor_user_id", unique=True, postgresql_where=text("decision_id IS NULL")),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("application.id", ondelete="CASCADE"), index=True)
    decision: Mapped[str] = mapped_column(String(20))
    cohort_id: Mapped[str | None] = mapped_column(ForeignKey("cohort.id"))
    reason: Mapped[str] = mapped_column(String(500))
    actor_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    decision_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("selection_decision.id"))
