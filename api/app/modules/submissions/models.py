"""KAN-56 (PF2-EDU-03): activities with a deadline and one submission per coder.

Rules (PO 23/11/2026, docs/producto/propuesta-KAN-56-KAN-263-desbloqueo-asistente.md):
- An assignment belongs to a cohort: its scope and the time zone of its deadline are the cohort's.
- One submission per (assignment, enrollment). It can be resubmitted until a teacher reviews it; the first date is kept.
- "On time", "late", "pending", "overdue" and "no data" are derived, never stored (see service.delivery_state).
- check_results holds pre-computed test results; the platform never runs submitted code. They describe one artifact:
  revision goes up on every resubmission, and replacing the artifact clears results that were not supplied again.
- A review names the revision the teacher saw; a review of an older revision is rejected (no stale reviews).
- Feedback text is not here: it belongs to KAN-191 (feedback_draft), published only after teacher approval.
"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, utcnow

ASSIGNMENT_STATUSES = ("draft", "published")
SUBMISSION_STATUSES = ("submitted", "reviewed")


class Assignment(Base):
    """An activity of a cohort with a deadline (stored in UTC, shown in the cohort's time zone)."""

    __tablename__ = "assignment"
    __table_args__ = (CheckConstraint(f"status IN {ASSIGNMENT_STATUSES}", name="ck_assignment_status"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    cohort_id: Mapped[str] = mapped_column(ForeignKey("cohort.id"), index=True)
    legacy_ref: Mapped[str | None] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text, default="")
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    rubric: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(10), default="published")
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Submission(Base):
    """The current delivery of one enrolled coder for one assignment."""

    __tablename__ = "submission"
    __table_args__ = (
        UniqueConstraint("assignment_id", "enrollment_id", name="uq_submission_assignment_enrollment"),
        CheckConstraint(f"status IN {SUBMISSION_STATUSES}", name="ck_submission_status"),
        CheckConstraint("portfolio_url IS NULL OR portfolio_url LIKE 'https://%'", name="ck_submission_portfolio_url"),
        CheckConstraint("revision >= 1", name="ck_submission_revision"),
        CheckConstraint(
            "(status = 'reviewed' AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)"
            " OR (status = 'submitted' AND reviewed_by IS NULL AND reviewed_at IS NULL)",
            name="ck_submission_review_shape",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    assignment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("assignment.id", ondelete="CASCADE"), index=True)
    enrollment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("enrollment.id"), index=True)
    portfolio_url: Mapped[str | None] = mapped_column(String(500))
    check_results: Mapped[dict | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(10), default="submitted")
    revision: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    first_submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    recorded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
