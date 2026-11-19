"""Prepared mappings, NOT imported by app.models until schema approval.

Requires a reviewed successor migration and Enrollment's (id, cohort_id) unique
key. Declaring mappings does not create tables or authorize database operations.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, ForeignKeyConstraint, Integer, Numeric, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, utcnow

STATUS_CHECK = "status IN ('present','full_absence','morning_absence','afternoon_absence')"
JUSTIFICATION_CHECK = "NOT (status = 'present' AND justified)"


class AttendanceSession(Base):
    __tablename__ = "attendance_session"
    __table_args__ = (
        UniqueConstraint("cohort_id", "session_date", "period", name="uq_attendance_session_cohort_date_period"),
        UniqueConstraint("id", "cohort_id", name="uq_attendance_session_id_cohort"),
        CheckConstraint("modality IN ('in_person','online')", name="ck_attendance_session_modality"),
        CheckConstraint("(period = 'full_day' AND duration_fraction = 1) OR (period IN ('morning','afternoon') AND duration_fraction = 0.5)", name="ck_attendance_session_period_duration"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    cohort_id: Mapped[str] = mapped_column(ForeignKey("cohort.id"), index=True)
    session_date: Mapped[date] = mapped_column(Date)
    period: Mapped[str] = mapped_column(String(10))
    duration_fraction: Mapped[Decimal] = mapped_column(Numeric(2, 1))
    modality: Mapped[str] = mapped_column(String(10))
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AttendanceRecord(Base):
    __tablename__ = "attendance_record"
    __table_args__ = (
        ForeignKeyConstraint(["session_id", "cohort_id"], ["attendance_session.id", "attendance_session.cohort_id"], name="fk_attendance_record_session_cohort"),
        ForeignKeyConstraint(["enrollment_id", "cohort_id"], ["enrollment.id", "enrollment.cohort_id"], name="fk_attendance_record_enrollment_cohort"),
        UniqueConstraint("session_id", "enrollment_id", name="uq_attendance_record_session_enrollment"),
        CheckConstraint(STATUS_CHECK, name="ck_attendance_record_status"),
        CheckConstraint(JUSTIFICATION_CHECK, name="ck_attendance_record_justified"),
        CheckConstraint("version >= 1", name="ck_attendance_record_version"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    cohort_id: Mapped[str] = mapped_column(String(20), index=True)
    session_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    enrollment_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    status: Mapped[str] = mapped_column(String(20))
    justified: Mapped[bool] = mapped_column(Boolean)
    recorded_by_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    version: Mapped[int] = mapped_column(Integer, default=1)


class AttendanceRevision(Base):
    """Append-only through the service; privileged direct SQL is not prevented."""

    __tablename__ = "attendance_revision"
    __table_args__ = (
        UniqueConstraint("record_id", "version", name="uq_attendance_revision_record_version"),
        CheckConstraint(STATUS_CHECK, name="ck_attendance_revision_status"),
        CheckConstraint(JUSTIFICATION_CHECK, name="ck_attendance_revision_justified"),
        CheckConstraint("version >= 1", name="ck_attendance_revision_version"),
        # The first version may have no reason; every correction (version > 1) must carry one.
        CheckConstraint(
            "(correction_reason IS NULL OR length(btrim(correction_reason)) BETWEEN 1 AND 500) AND (version = 1 OR correction_reason IS NOT NULL)",
            name="ck_attendance_revision_reason",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    record_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("attendance_record.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))
    justified: Mapped[bool] = mapped_column(Boolean)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    correction_reason: Mapped[str | None] = mapped_column(String(500))
