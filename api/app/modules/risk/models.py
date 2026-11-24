"""Synthetic model evidence and human support records, without automated learner actions."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, utcnow


class RiskAlert(Base):
    __tablename__ = "risk_alert"
    __table_args__ = (
        UniqueConstraint("enrollment_id", "model_hash", "cutoff", name="uq_risk_alert_observation"),
        CheckConstraint("length(model_hash) = 64 AND length(trim(model_version)) > 0", name="ck_risk_alert_provenance"),
        CheckConstraint("synthetic_only AND human_review_only AND NOT validated_for_people", name="ck_risk_alert_synthetic"),
        CheckConstraint("review_state IN ('pending', 'in_review', 'closed')", name="ck_risk_alert_review_state"),
        CheckConstraint("(status = 'scored' AND synthetic_proxy_score BETWEEN 0 AND 1 AND synthetic_proxy_score IS NOT NULL"
                        " AND experimental_support_signal IS NOT NULL AND abstention_reason IS NULL) OR"
                        " (status = 'abstained' AND synthetic_proxy_score IS NULL AND experimental_support_signal IS NULL"
                        " AND abstention_reason IS NOT NULL AND length(trim(abstention_reason)) > 0)", name="ck_risk_alert_score_shape"),
        CheckConstraint("unjustified_absence_days IS NULL OR unjustified_absence_days >= 0", name="ck_risk_alert_unjustified"),
        CheckConstraint("justified_absence_days IS NULL OR justified_absence_days >= 0", name="ck_risk_alert_justified"),
        CheckConstraint("attendance_unknown_fraction IS NULL OR attendance_unknown_fraction BETWEEN 0 AND 1", name="ck_risk_alert_unknown"),
        CheckConstraint("mean_competency_level IS NULL OR mean_competency_level BETWEEN 1 AND 3", name="ck_risk_alert_competency"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    enrollment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("enrollment.id"), index=True)
    model_version: Mapped[str] = mapped_column(String(80))
    model_hash: Mapped[str] = mapped_column(String(64))
    cutoff: Mapped[date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(12))
    synthetic_proxy_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 7))
    experimental_support_signal: Mapped[bool | None] = mapped_column(Boolean)
    abstention_reason: Mapped[str | None] = mapped_column(String(120))
    unjustified_absence_days: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    justified_absence_days: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    attendance_unknown_fraction: Mapped[Decimal | None] = mapped_column(Numeric(8, 7))
    mean_competency_level: Mapped[Decimal | None] = mapped_column(Numeric(4, 2))
    synthetic_only: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    human_review_only: Mapped[bool] = mapped_column(Boolean, default=True, server_default=text("true"))
    validated_for_people: Mapped[bool] = mapped_column(Boolean, default=False, server_default=text("false"))
    review_state: Mapped[str] = mapped_column(String(12), default="pending", server_default="pending")
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Intervention(Base):
    __tablename__ = "intervention"
    __table_args__ = (
        CheckConstraint("kind IN ('contact', 'support', 'closure')", name="ck_intervention_kind"),
        CheckConstraint("length(trim(note)) BETWEEN 1 AND 500", name="ck_intervention_note"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    alert_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("risk_alert.id"), index=True)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), index=True)
    kind: Mapped[str] = mapped_column(String(12))
    note: Mapped[str] = mapped_column(String(500))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
