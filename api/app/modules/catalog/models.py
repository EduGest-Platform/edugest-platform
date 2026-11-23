from datetime import date

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

# Catalog IDs are stable strings shared with the web prototype (P-IA, COH-IA…).


class Program(Base):
    __tablename__ = "program"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    descripcion: Mapped[str] = mapped_column(Text, default="")


class Call(Base):
    """Convocatoria: the scope of pre-selection and selection."""

    __tablename__ = "call"
    __table_args__ = (
        CheckConstraint("estado IN ('abierta','cerrada')", name="ck_call_estado"),
        CheckConstraint("silence_days BETWEEN 1 AND 365", name="ck_call_silence_days"),
        CheckConstraint("silence_max_contacts BETWEEN 1 AND 20", name="ck_call_silence_max_contacts"),
        CheckConstraint("silence_warning_contacts BETWEEN 1 AND silence_max_contacts", name="ck_call_silence_warning_contacts"),
        CheckConstraint("selection_quorum BETWEEN 1 AND 5", name="ck_call_selection_quorum"),
    )
    id: Mapped[str] = mapped_column(String(30), primary_key=True)
    program_id: Mapped[str] = mapped_column(ForeignKey("program.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(160))
    codigo_prefix: Mapped[str] = mapped_column(String(10), unique=True)
    opens_on: Mapped[date] = mapped_column(Date)
    closes_on: Mapped[date] = mapped_column(Date)
    plazas: Mapped[int] = mapped_column(Integer)
    estado: Mapped[str] = mapped_column(String(10), default="abierta")
    # Per-call counter for human-readable application codes (incremented under row lock).
    next_seq: Mapped[int] = mapped_column(Integer, default=1)
    # Pre-selection silence policy (KAN-153). Editable per call; a decision stores the values it used.
    silence_days: Mapped[int] = mapped_column(Integer, default=30, server_default=text("30"))
    silence_max_contacts: Mapped[int] = mapped_column(Integer, default=4, server_default=text("4"))
    # Early, light alert (PO 19/11/2026): unanswered attempts that already flag the application, with no waiting days.
    silence_warning_contacts: Mapped[int] = mapped_column(Integer, default=2, server_default=text("2"))
    # Melissa round 3 Q11 (PO 23/11/2026): different people who must agree on a selection decision; default two.
    selection_quorum: Mapped[int] = mapped_column(Integer, default=2, server_default=text("2"))


# Spain (peninsula, Canary Islands) and Portugal (PO 19/11/2026). Decides which day is "today" for a cohort.
COHORT_TIMEZONES = ("Europe/Madrid", "Atlantic/Canary", "Europe/Lisbon")


class Cohort(Base):
    __tablename__ = "cohort"
    __table_args__ = (CheckConstraint(f"timezone IN {COHORT_TIMEZONES}", name="ck_cohort_timezone"),)
    id: Mapped[str] = mapped_column(String(20), primary_key=True)
    program_id: Mapped[str] = mapped_column(ForeignKey("program.id"), index=True)
    call_id: Mapped[str | None] = mapped_column(ForeignKey("call.id"))
    nombre: Mapped[str] = mapped_column(String(160))
    inicio: Mapped[date] = mapped_column(Date)
    fin: Mapped[date] = mapped_column(Date)
    timezone: Mapped[str] = mapped_column(String(40), default="Europe/Madrid", server_default="Europe/Madrid")
