import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, utcnow


class Enrollment(Base):
    """Matrícula: links the same Person to a Cohort. Created from an admission decision from F2 onwards."""

    __tablename__ = "enrollment"
    __table_args__ = (
        UniqueConstraint("person_id", "cohort_id", name="uq_enrollment_person_cohort"),
        CheckConstraint("estado IN ('activa','finalizada','baja_voluntaria')", name="ck_enrollment_estado"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("person.id"), index=True)
    cohort_id: Mapped[str] = mapped_column(ForeignKey("cohort.id"), index=True)
    application_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("application.id"))
    estado: Mapped[str] = mapped_column(String(20), default="activa")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
