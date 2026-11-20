import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Shift = Literal["manana", "tarde", "completa"]
Status = Literal["presente", "retraso", "ausente"]
Justification = Literal["justificada", "no_justificada"]
Modality = Literal["presencial", "online"]

SUMMARY_RULE = (
    "Día completo = 1, mañana o tarde = 0,5. Solo cuentan sesiones ya celebradas, según la hora local de la cohorte. "
    "Llegar con retraso cuenta como asistencia y se suma también aparte. "
    "Una sesión celebrada sin registro es «sin dato», nunca ausencia. Justificadas y no justificadas se suman por separado."
)


def _strip(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


class SessionWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_date: date
    shift: Shift = Field(description="manana o tarde pesan 0,5; completa pesa 1")


class RecordWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Status
    modality: Modality | None = Field(default=None, description="Obligatoria si asistió (presente o retraso); vacía si está ausente")
    justification: Justification | None = Field(default=None, description="Obligatoria si está ausente; vacía si asistió")
    reason: str | None = Field(default=None, max_length=300, description="Motivo de la corrección. Obligatorio al cambiar un registro. Sin datos de salud ni personales.")

    @field_validator("reason", mode="before")
    @classmethod
    def _trim_reason(cls, value: object) -> object:
        return _strip(value)


class RecordOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    enrollment_id: uuid.UUID
    status: Status
    modality: Modality | None
    justification: Justification | None
    version: int
    updated_at: datetime


class SessionOut(BaseModel):
    id: uuid.UUID
    cohort_id: str
    session_date: date
    shift: Shift
    duration_fraction: float
    held: bool = Field(description="La sesión ya se ha celebrado (fecha anterior o igual a hoy en la zona horaria de la cohorte)")
    records: list[RecordOut]


class SessionList(BaseModel):
    cohort_id: str
    items: list[SessionOut]


class RevisionOut(BaseModel):
    version: int
    status: Status
    modality: Modality | None
    justification: Justification | None
    reason: str | None
    changed_by: str | None
    changed_at: datetime


class RevisionList(BaseModel):
    record_id: uuid.UUID
    items: list[RevisionOut]


class EnrollmentAttendance(BaseModel):
    enrollment_id: uuid.UUID
    held_days: float = Field(description="Suma de fracciones de las sesiones celebradas")
    attended_days: float = Field(description="Asistencia a tiempo más con retraso")
    late_days: float = Field(description="Parte de attended_days en la que llegó con retraso")
    attended_in_person_days: float
    attended_online_days: float
    justified_absence_days: float
    unjustified_absence_days: float
    unrecorded_days: float = Field(description="Sesiones celebradas sin registro (sin dato)")
    attendance_rate: float | None = Field(description="Asistido / registrado. Nulo si no hay registros")


class CohortAttendance(BaseModel):
    """Cohort-level totals for coordination. All values are null when the group is too small to show."""

    enrollments: int | None
    suppressed: bool
    min_group_size: int
    attended_days: float | None = None
    late_days: float | None = None
    justified_absence_days: float | None = None
    unjustified_absence_days: float | None = None
    unrecorded_days: float | None = None
    attendance_rate: float | None = None


class AttendanceSummary(BaseModel):
    """Contract of get_attendance_summary for the assistant: totals only, no names."""

    cohort_id: str
    timezone: str
    date_from: date | None
    date_to: date | None
    rule: str = SUMMARY_RULE
    items: list[EnrollmentAttendance] = Field(description="Totales por matrícula. Vacío para coordinación, que solo ve el agregado")
    cohort_totals: CohortAttendance
