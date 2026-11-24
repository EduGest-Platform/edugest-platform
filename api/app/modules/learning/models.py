import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, utcnow


class Enrollment(Base):
    """Matrícula: links the same Person to a Cohort. Created from an admission decision from F2 onwards."""

    __tablename__ = "enrollment"
    __table_args__ = (
        UniqueConstraint("person_id", "cohort_id", name="uq_enrollment_person_cohort"),
        CheckConstraint("estado IN ('activa','finalizada','baja_voluntaria')", name="ck_enrollment_estado"),
        CheckConstraint("documentation_state IN ('pending','accredited')", name="ck_enrollment_documentation_state"),
        CheckConstraint("documentation_version >= 1", name="ck_enrollment_documentation_version"),
        CheckConstraint("(documentation_state = 'pending' AND documentation_accredited_by IS NULL AND documentation_accredited_at IS NULL) OR "
                        "(documentation_state = 'accredited' AND documentation_accredited_by IS NOT NULL AND documentation_accredited_at IS NOT NULL)",
                        name="ck_enrollment_documentation_evidence"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("person.id"), index=True)
    cohort_id: Mapped[str] = mapped_column(ForeignKey("cohort.id"), index=True)
    application_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("application.id"))
    estado: Mapped[str] = mapped_column(String(20), default="activa")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    # Documentary evidence is separate from academic lifecycle and never inferred from admission.
    documentation_state: Mapped[str] = mapped_column(String(12), default="pending", server_default="pending")
    documentation_version: Mapped[int] = mapped_column(Integer, default=1, server_default=text("1"))
    documentation_accredited_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    documentation_accredited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
