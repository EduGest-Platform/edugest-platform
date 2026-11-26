"""KAN-191 / KAN-67: versioned feedback drafts for one submission, published only after teacher approval.

Every version keeps its provenance: the submission revision it describes, a copy of the rubric and of the
pre-computed test results, who wrote it (template or teacher) and who approved it. Nothing is overwritten:
an edit creates a new version. A draft never uses the portfolio URL or any submitted content.
"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, utcnow

DRAFT_SOURCES = ("template", "teacher")
DRAFT_STATUSES = ("draft", "approved")


class FeedbackDraft(Base):
    """One version of the feedback for one submission. Only an approved version is ever shown to the coder."""

    __tablename__ = "feedback_draft"
    __table_args__ = (
        UniqueConstraint("submission_id", "version", name="uq_feedback_draft_version"),
        CheckConstraint(f"source IN {DRAFT_SOURCES}", name="ck_feedback_draft_source"),
        CheckConstraint(f"status IN {DRAFT_STATUSES}", name="ck_feedback_draft_status"),
        CheckConstraint("version >= 1 AND submission_revision >= 1", name="ck_feedback_draft_numbers"),
        CheckConstraint("length(btrim(body)) > 0", name="ck_feedback_draft_body"),
        CheckConstraint(
            "(status = 'approved' AND num_nonnulls(approved_by, approved_at) = 2)"
            " OR (status = 'draft' AND num_nonnulls(approved_by, approved_at) = 0)",
            name="ck_feedback_draft_approval",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    submission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("submission.id", ondelete="CASCADE"), index=True)
    submission_revision: Mapped[int] = mapped_column(Integer)
    version: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(10), default="draft")
    body: Mapped[str] = mapped_column(Text)
    rubric: Mapped[list] = mapped_column(JSON)
    check_results: Mapped[dict] = mapped_column(JSON)
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
