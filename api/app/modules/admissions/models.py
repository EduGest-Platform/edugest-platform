import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, String, Text, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import ARRAY
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
# Outcome of a contact attempt: only «sin_respuesta» attempts count towards a silence review.
CONTACT_RESULTS = ("respondida", "sin_respuesta")


class Application(Base):
    """One application per Person and Call.

    A public application never joins an existing Person on its own (KAN-274): it gets a new record and, when the email
    is already known, an IdentityReview that a member of staff resolves.
    """

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
        CheckConstraint(f"resultado IS NULL OR (tipo = 'contacto' AND resultado IN {CONTACT_RESULTS})", name="ck_application_event_resultado"),
        # KAN-272 (PO 26/11/2026): a next action is optional, only on contacts, and always complete.
        CheckConstraint(
            "num_nonnulls(next_action, next_action_owner_id, next_action_due_on) = 0 OR "
            "(num_nonnulls(next_action, next_action_owner_id, next_action_due_on) = 3 "
            "AND tipo = 'contacto' AND length(btrim(next_action)) > 0)",
            name="ck_application_event_next_action",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("application.id", ondelete="CASCADE"), index=True)
    tipo: Mapped[str] = mapped_column(String(20))
    canal: Mapped[str | None] = mapped_column(String(20))
    resultado: Mapped[str | None] = mapped_column(String(20))
    resumen: Mapped[str] = mapped_column(String(500))
    next_action: Mapped[str | None] = mapped_column(String(200))
    next_action_owner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    next_action_due_on: Mapped[date | None] = mapped_column(Date)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


IDENTITY_DECISIONS = ("misma_persona", "persona_distinta")


class IdentityReview(Base):
    """KAN-274: an application whose email already belongs to another record, waiting for a person to decide.

    The decision is recorded once, with its author, date and reason. Only «misma_persona» moves the application to the
    linked Person; `original_person_id` keeps the record created at intake, so what was submitted is never lost.
    """

    __tablename__ = "identity_review"
    __table_args__ = (
        CheckConstraint(f"decision IS NULL OR decision IN {IDENTITY_DECISIONS}", name="ck_identity_review_decision"),
        CheckConstraint("num_nonnulls(decision, reason, decided_by, decided_at) IN (0, 4)", name="ck_identity_review_complete"),
        CheckConstraint("(linked_person_id IS NOT NULL) = (decision IS NOT DISTINCT FROM 'misma_persona')", name="ck_identity_review_link"),
        CheckConstraint("reason IS NULL OR length(btrim(reason)) > 0", name="ck_identity_review_reason"),
        CheckConstraint("cardinality(candidate_person_ids) > 0", name="ck_identity_review_candidates"),
    )
    application_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("application.id", ondelete="CASCADE"), primary_key=True)
    original_person_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("person.id"))
    # Fixed at intake, so which records are compared never depends on clocks.
    candidate_person_ids: Mapped[list[uuid.UUID]] = mapped_column(ARRAY(Uuid))
    decision: Mapped[str | None] = mapped_column(String(20))
    linked_person_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("person.id"))
    reason: Mapped[str | None] = mapped_column(String(500))
    decided_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
