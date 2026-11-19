"""Typed attendance contract. Unknown records are never interpreted as attendance."""

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

SessionPeriod = Literal["full_day", "morning", "afternoon"]
AttendanceStatus = Literal["present", "full_absence", "morning_absence", "afternoon_absence"]
Modality = Literal["in_person", "online"]
ABSENCE_DAYS = {
    "present": Decimal("0"), "full_absence": Decimal("1"),
    "morning_absence": Decimal("0.5"), "afternoon_absence": Decimal("0.5"),
}
PERIOD_DURATION = {"full_day": Decimal("1"), "morning": Decimal("0.5"), "afternoon": Decimal("0.5")}
PERIOD_STATUSES = {
    "full_day": frozenset(ABSENCE_DAYS),
    "morning": frozenset({"present", "morning_absence"}),
    "afternoon": frozenset({"present", "afternoon_absence"}),
}


class AttendanceSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_date: date
    period: SessionPeriod
    modality: Modality


class AttendanceRecordWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    status: AttendanceStatus
    justified: bool = Field(strict=True)
    expected_version: int | None = Field(default=None, ge=1, strict=True)
    correction_reason: str | None = Field(
        default=None, min_length=1, max_length=500,
        description="Obligatorio solo al corregir (con expected_version). Motivo operativo; no incluir datos de salud ni situación personal; no se expone al asistente.",
    )

    @model_validator(mode="after")
    def validate_justification(self):
        if self.status == "present" and self.justified:
            raise ValueError("A presence cannot be a justified absence")
        if self.expected_version is not None and not self.correction_reason:
            raise ValueError("Una corrección necesita un motivo")
        return self


class AttendanceSessionOut(BaseModel):
    id: UUID
    cohort_id: str
    session_date: date
    period: SessionPeriod
    duration_fraction: Decimal
    modality: Modality


class AttendanceRecordOut(BaseModel):
    id: UUID
    session_id: UUID
    enrollment_id: UUID
    status: AttendanceStatus
    justified: bool
    absence_days: Decimal
    recorded_at: datetime
    version: int


class AttendanceSummary(BaseModel):
    """Only recorded amounts; data_state/unknown duration describe their coverage."""

    enrollment_id: UUID
    cohort_id: str
    date_from: date
    date_to: date
    as_of: datetime
    period_timezone: Literal["Europe/Madrid"] = "Europe/Madrid"
    unit: Literal["equivalent_days"] = "equivalent_days"
    counting_rule: Literal["full_absence=1; morning_absence=0.5; afternoon_absence=0.5; missing=unknown"] = (
        "full_absence=1; morning_absence=0.5; afternoon_absence=0.5; missing=unknown"
    )
    source: Literal["postgresql", "synthetic_fixture"]
    data_state: Literal["no_data", "partial", "complete"]
    held_sessions: int
    recorded_sessions: int
    unrecorded_sessions: int
    scheduled_days: Decimal
    recorded_days: Decimal
    unknown_days: Decimal
    recorded_absence_days: Decimal | None
    justified_absence_days: Decimal | None
    unjustified_absence_days: Decimal | None
    latest_recorded_at: datetime | None
