import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, utcnow


class CallRequirement(Base):
    """An immutable definition; changing a rule creates a new reference and version."""

    __tablename__ = "call_requirement"
    __table_args__ = (
        UniqueConstraint("call_id", "ref", name="uq_call_requirement_ref"),
        UniqueConstraint("call_id", "code", "version", name="uq_call_requirement_code_version"),
        CheckConstraint("kind IN ('required', 'recommended')", name="ck_call_requirement_kind"),
        CheckConstraint("version >= 1", name="ck_call_requirement_version"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    call_id: Mapped[str] = mapped_column(ForeignKey("call.id"), index=True)
    ref: Mapped[str] = mapped_column(String(60))
    code: Mapped[str] = mapped_column(String(60))
    version: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(20))
    funder: Mapped[str | None] = mapped_column(String(120))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

RESULTS = ("pending", "met", "not_met", "exception_under_review", "exception_approved")
COMPLETED_RESULTS = RESULTS[1:]
EXCEPTION_RESULTS = ("exception_under_review", "exception_approved")


class RequirementReview(Base):
    """Latest human review of one requirement of one application. It never changes the application stage."""

    __tablename__ = "requirement_review"
    __table_args__ = (
        UniqueConstraint("application_id", "requirement_ref", name="uq_requirement_review_application_ref"),
        CheckConstraint(f"result IN {RESULTS}", name="ck_requirement_review_result"),
        # A pending record has no author, date or reason; a completed one has all three.
        CheckConstraint(
            "(result = 'pending' AND reviewer_user_id IS NULL AND reviewed_at IS NULL AND reason IS NULL) OR "
            "(result <> 'pending' AND reviewer_user_id IS NOT NULL AND reviewed_at IS NOT NULL "
            "AND reason IS NOT NULL AND length(btrim(reason)) > 0)",
            name="ck_requirement_review_completed",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("application.id", ondelete="CASCADE"), index=True)
    # Opaque requirement identifier. It becomes a reference to the immutable requirement version when KAN-135 lands.
    requirement_ref: Mapped[str] = mapped_column(String(60))
    # Legacy rows remain unverified until an explicit review binds an existing definition.
    requirement_definition_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("call_requirement.id"))
    result: Mapped[str] = mapped_column(String(30), default="pending")
    reviewer_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str | None] = mapped_column(String(500))
    # Optimistic concurrency token: it grows by one with every revision.
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RequirementReviewRevision(Base):
    """Immutable history: one row per saved review, so earlier reviewer, result, date and reason are never lost."""

    __tablename__ = "requirement_review_revision"
    __table_args__ = (
        UniqueConstraint("review_id", "revision", name="uq_requirement_review_revision_number"),
        CheckConstraint(f"result IN {COMPLETED_RESULTS}", name="ck_requirement_review_revision_result"),
        CheckConstraint("length(btrim(reason)) > 0", name="ck_requirement_review_revision_reason"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    review_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("requirement_review.id", ondelete="CASCADE"), index=True)
    requirement_definition_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("call_requirement.id"))
    revision: Mapped[int] = mapped_column(Integer)
    result: Mapped[str] = mapped_column(String(30))
    reviewer_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    reviewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str] = mapped_column(String(500))
