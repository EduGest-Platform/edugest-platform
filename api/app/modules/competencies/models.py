"""KAN-57 (PF2-EDU-04): versioned competency tree per bootcamp (program) and level 1–3 assessments per coder.

- A program has numbered framework versions. Only a draft can be edited; publishing freezes it and archives the
  previous published version, which stays readable so old assessments remain traceable.
- Each competency carries the descriptors of levels 1–3: that is the rubric the assessment used.
- A cohort is pinned to one framework version of its own program, so it never inherits another course's tree.
- Assessments are append-only: a new level is a new row with assessor and date; the latest one is the current level.
  No assessment means "sin evaluar", never level 0.
"""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, SmallInteger, String, Text, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, utcnow

FRAMEWORK_STATES = ("borrador", "publicada", "archivada")


class CompetencyFramework(Base):
    """One version of a program's competency tree."""

    __tablename__ = "competency_framework"
    __table_args__ = (
        UniqueConstraint("program_id", "version", name="uq_competency_framework_version"),
        CheckConstraint(f"estado IN {FRAMEWORK_STATES}", name="ck_competency_framework_estado"),
        CheckConstraint("version >= 1", name="ck_competency_framework_version"),
        CheckConstraint("(estado = 'borrador') = (published_at IS NULL)", name="ck_competency_framework_published_at"),
        # At most one published version per program.
        Index("uq_competency_framework_one_published", "program_id", unique=True, postgresql_where=text("estado = 'publicada'")),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    program_id: Mapped[str] = mapped_column(ForeignKey("program.id"), index=True)
    version: Mapped[int] = mapped_column(Integer)
    estado: Mapped[str] = mapped_column(String(10), default="borrador")
    based_on_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("competency_framework.id"))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Competency(Base):
    """A competency (C1–C10 in the briefing) inside one framework version, with its level 1–3 rubric."""

    __tablename__ = "competency"
    __table_args__ = (
        UniqueConstraint("framework_id", "codigo", name="uq_competency_framework_codigo"),
        CheckConstraint("codigo ~ '^C[1-9][0-9]?$'", name="ck_competency_codigo"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    framework_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("competency_framework.id", ondelete="CASCADE"), index=True)
    codigo: Mapped[str] = mapped_column(String(4))
    nombre: Mapped[str] = mapped_column(String(160))
    descripcion: Mapped[str] = mapped_column(Text, default="")
    level_1: Mapped[str] = mapped_column(Text)
    level_2: Mapped[str] = mapped_column(Text)
    level_3: Mapped[str] = mapped_column(Text)
    orden: Mapped[int] = mapped_column(Integer)


class CohortCompetencyFramework(Base):
    """Which framework version a cohort is assessed against (one per cohort)."""

    __tablename__ = "cohort_competency_framework"
    cohort_id: Mapped[str] = mapped_column(ForeignKey("cohort.id"), primary_key=True)
    framework_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("competency_framework.id"), index=True)
    assigned_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CompetencyAssessment(Base):
    """Append-only: a teacher's level 1–3 for one coder on one competency, with evidence, assessor and date."""

    __tablename__ = "competency_assessment"
    __table_args__ = (
        CheckConstraint("level BETWEEN 1 AND 3", name="ck_competency_assessment_level"),
        CheckConstraint("length(btrim(evidence)) > 0", name="ck_competency_assessment_evidence"),
        Index("ix_competency_assessment_enrollment_competency", "enrollment_id", "competency_id", "assessed_at"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    enrollment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("enrollment.id"))
    competency_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("competency.id"), index=True)
    level: Mapped[int] = mapped_column(SmallInteger)
    evidence: Mapped[str] = mapped_column(String(500))
    assessed_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"))
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
