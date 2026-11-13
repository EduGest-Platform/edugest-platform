import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, utcnow

# Same vocabulary as the web prototype (Applications.tsx), plus «retirada».
STAGES = (
    "enviada",
    "requisitos_en_revision",
    "convocada",
    "evaluacion_en_curso",
    "pendiente_decision_humana",
    "admitida",
    "lista_espera",
    "no_admitida",
    "retirada",
)
EVENT_TYPES = ("creada", "contacto", "nota", "recordatorio", "cambio_etapa")
CHANNELS = ("email", "telefono", "presencial", "videollamada")


class Application(Base):
    """One application per Person and Call. The Person is reused across calls (no duplicate expedientes)."""

    __tablename__ = "application"
    __table_args__ = (
        UniqueConstraint("person_id", "call_id", name="uq_application_person_call"),
        CheckConstraint(f"stage IN {STAGES}", name="ck_application_stage"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    codigo: Mapped[str] = mapped_column(String(20), unique=True)
    legacy_ref: Mapped[str | None] = mapped_column(String(20), unique=True)
    person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("person.id"), index=True)
    call_id: Mapped[str] = mapped_column(ForeignKey("call.id"), index=True)
    stage: Mapped[str] = mapped_column(String(40), default="enviada")
    motivacion: Mapped[str] = mapped_column(Text)
    disponibilidad: Mapped[str] = mapped_column(String(20))
    acepta_datos_sinteticos: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class ApplicationEvent(Base):
    """CRM history: contacts, notes, reminders and stage changes, with author and timestamp."""

    __tablename__ = "application_event"
    __table_args__ = (
        CheckConstraint(f"tipo IN {EVENT_TYPES}", name="ck_application_event_tipo"),
        CheckConstraint(f"canal IS NULL OR canal IN {CHANNELS}", name="ck_application_event_canal"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("application.id", ondelete="CASCADE"), index=True)
    tipo: Mapped[str] = mapped_column(String(20))
    canal: Mapped[str | None] = mapped_column(String(20))
    resumen: Mapped[str] = mapped_column(String(500))
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
