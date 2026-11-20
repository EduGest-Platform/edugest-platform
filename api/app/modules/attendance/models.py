"""KAN-55 (PF2-EDU-02): attendance per session or half-day, with justification and audited corrections.

Rules (AGENTS.md, projectplan): a full day weighs 1, a morning or afternoon weighs 0.5; justified and unjustified
absences are kept apart; a held session without a record is "sin dato", never an absence. Being late ("retraso",
PO 19/11/2026) counts as attended but is also totalled on its own.
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, utcnow

SHIFTS = ("manana", "tarde", "completa")
STATUSES = ("presente", "retraso", "ausente")
JUSTIFICATIONS = ("justificada", "no_justificada")
MODALITIES = ("presencial", "online")

# A record is either "attended (present or late), in person or online" or "absent, justified or not". Nothing in between.
_RECORD_SHAPE = (
    "(status IN ('presente', 'retraso') AND modality IS NOT NULL AND justification IS NULL)"
    " OR (status = 'ausente' AND modality IS NULL AND justification IS NOT NULL)"
)


class AttendanceSession(Base):
    """A teaching slot of a cohort: a morning, an afternoon or a full day. Its weight is fixed by the shift."""

    __tablename__ = "attendance_session"
    __table_args__ = (
        UniqueConstraint("cohort_id", "session_date", "shift", name="uq_attendance_session_slot"),
        CheckConstraint(f"shift IN {SHIFTS}", name="ck_attendance_session_shift"),
        CheckConstraint(
            "(shift = 'completa' AND duration_fraction = 1) OR (shift IN ('manana','tarde') AND duration_fraction = 0.5)",
            name="ck_attendance_session_fraction",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    cohort_id: Mapped[str] = mapped_column(ForeignKey("cohort.id"), index=True)
    session_date: Mapped[date] = mapped_column(Date)
    shift: Mapped[str] = mapped_column(String(10))
    duration_fraction: Mapped[Decimal] = mapped_column(Numeric(2, 1))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AttendanceRecord(Base):
    """Current attendance of one enrolled coder in one session. Every change is kept in AttendanceRecordRevision."""

    __tablename__ = "attendance_record"
    __table_args__ = (
        UniqueConstraint("session_id", "enrollment_id", name="uq_attendance_record_session_enrollment"),
        CheckConstraint(f"status IN {STATUSES}", name="ck_attendance_record_status"),
        CheckConstraint(f"justification IS NULL OR justification IN {JUSTIFICATIONS}", name="ck_attendance_record_justification"),
        CheckConstraint(f"modality IS NULL OR modality IN {MODALITIES}", name="ck_attendance_record_modality"),
        CheckConstraint(_RECORD_SHAPE, name="ck_attendance_record_shape"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("attendance_session.id"), index=True)
    enrollment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("enrollment.id"), index=True)
    status: Mapped[str] = mapped_column(String(10))
    modality: Mapped[str | None] = mapped_column(String(10))
    justification: Mapped[str | None] = mapped_column(String(15))
    version: Mapped[int] = mapped_column(Integer, default=1)
    recorded_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AttendanceRecordRevision(Base):
    """Append-only history: the values a record had after each save (version 1 = first registration)."""

    __tablename__ = "attendance_record_revision"
    __table_args__ = (
        UniqueConstraint("record_id", "version", name="uq_attendance_record_revision_version"),
        CheckConstraint(_RECORD_SHAPE, name="ck_attendance_record_revision_shape"),
        CheckConstraint("version = 1 OR length(btrim(coalesce(reason, ''))) > 0", name="ck_attendance_record_revision_reason"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    record_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("attendance_record.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(10))
    modality: Mapped[str | None] = mapped_column(String(10))
    justification: Mapped[str | None] = mapped_column(String(15))
    # Required for corrections (version > 1). Operational reason only, never health or personal details.
    reason: Mapped[str | None] = mapped_column(String(300))
    changed_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
