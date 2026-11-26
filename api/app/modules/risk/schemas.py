import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ReviewState = Literal["pending", "in_review", "closed"]
InterventionKind = Literal["contact", "support", "closure"]


class RiskAlertOut(BaseModel):
    id: uuid.UUID
    learner_name: str
    model_version: str
    cutoff: date
    status: Literal["scored", "abstained"]
    experimental_support_signal: bool | None
    abstention_reason: str | None
    unjustified_absence_days: float | None
    justified_absence_days: float | None
    attendance_unknown_fraction: float | None
    mean_competency_level: float | None
    review_state: ReviewState
    assigned_to: str | None
    synthetic_only: Literal[True] = True


class RiskAlertList(BaseModel):
    items: list[RiskAlertOut]
    total: int


class InterventionWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    kind: InterventionKind
    note: str = Field(min_length=1, max_length=500)
    expected_state: ReviewState


class InterventionOut(BaseModel):
    id: uuid.UUID
    kind: InterventionKind
    note: str
    occurred_at: datetime
    actor: str


class AlertReviewOut(BaseModel):
    alert: RiskAlertOut
    interventions: list[InterventionOut]
