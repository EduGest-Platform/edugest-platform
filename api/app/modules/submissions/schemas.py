import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DeliveryState = Literal["on_time", "late", "pending", "overdue"]

DELIVERY_RULE = (
    "Plazo en la hora local de la cohorte. Entregada antes del plazo = a tiempo; después = tarde. "
    "Sin entrega y plazo abierto = pendiente; sin entrega y plazo vencido = vencida. "
    "Se puede reentregar hasta la revisión docente; se conserva la primera fecha."
)


def _strip(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


class AssignmentWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=3, max_length=160)
    description: str = Field(default="", max_length=4000)
    due_at: datetime = Field(description="Plazo con zona horaria (ISO 8601)")
    rubric: list[str] = Field(default_factory=list, max_length=20, description="Criterios de la rúbrica")
    status: Literal["draft", "published"] = "published"

    @field_validator("title", "description", mode="before")
    @classmethod
    def _trim(cls, value: object) -> object:
        return _strip(value)

    @field_validator("due_at")
    @classmethod
    def _aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("El plazo debe indicar la zona horaria")
        return value


class AssignmentOut(BaseModel):
    id: uuid.UUID
    cohort_id: str
    title: str
    description: str
    due_at: datetime
    rubric: list[str]
    status: str


class AssignmentList(BaseModel):
    cohort_id: str
    timezone: str
    items: list[AssignmentOut]


class CheckResults(BaseModel):
    """Pre-computed automated checks. The platform never runs submitted code."""

    model_config = ConfigDict(extra="forbid")

    passed: int = Field(ge=0)
    total: int = Field(gt=0, le=10000)

    @model_validator(mode="after")
    def _passed_within_total(self) -> "CheckResults":
        if self.passed > self.total:
            raise ValueError("passed no puede ser mayor que total")
        return self


class SubmissionWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    portfolio_url: str | None = Field(default=None, max_length=500, description="Opcional; debe empezar por https://")
    check_results: CheckResults | None = None

    @field_validator("portfolio_url", mode="before")
    @classmethod
    def _valid_url(cls, value: object) -> object:
        value = _strip(value)
        if value in ("", None):
            return None
        if not isinstance(value, str) or not value.startswith("https://") or " " in value or len(value) < 12:
            raise ValueError("La URL del portfolio debe empezar por https://")
        return value


class SubmissionOut(BaseModel):
    id: uuid.UUID
    assignment_id: uuid.UUID
    enrollment_id: uuid.UUID
    portfolio_url: str | None
    check_results: CheckResults | None
    status: str
    revision: int = Field(description="Sube en cada reentrega; la revisión debe indicar la que vio el docente")
    first_submitted_at: datetime
    submitted_at: datetime
    late: bool
    reviewed_at: datetime | None


class ReviewWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1, description="Versión de la entrega que ha revisado el docente")


class EnrollmentDelivery(BaseModel):
    """One assignment from one coder's point of view: the derived state plus the submission if there is one."""

    assignment_id: uuid.UUID
    title: str
    due_at: datetime
    state: DeliveryState
    reviewed: bool
    submission: SubmissionOut | None


class EnrollmentSubmissions(BaseModel):
    enrollment_id: uuid.UUID
    cohort_id: str
    rule: str = DELIVERY_RULE
    items: list[EnrollmentDelivery]
