import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, AwareDatetime, ConfigDict, Field, JsonValue


class AutomationExecutionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    application_id: uuid.UUID
    call_id: str
    kind: Literal["requirement_prefilter"]
    rule_version: str
    idempotency_key: str
    outcome: Literal["human_review", "no_action"]
    stage_at_evaluation: str
    # Historical JSON stays readable when the live prefilter schema gains required fields.
    snapshot: dict[str, JsonValue]
    evaluated_at: datetime


class AutomationExecutionList(BaseModel):
    application_id: uuid.UUID
    items: list[AutomationExecutionOut]
    total: int
    limit: int


class ReminderSimulationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    task_ref: str = Field(min_length=1, max_length=80, pattern=r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")
    kind: Literal["documentation", "exercises"]
    due_at: AwareDatetime
    synthetic_only: Literal[True]


class SimulatedReminderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    application_id: uuid.UUID
    call_id: str
    task_ref: str
    kind: Literal["documentation", "exercises"]
    due_at: datetime
    rule_version: str
    simulated_at: datetime
    simulated_only: Literal[True] = True
    schedule_source: Literal["staff_entered"] = "staff_entered"


class ReminderSimulationResult(BaseModel):
    simulated_only: Literal[True] = True
    outcome: Literal["simulated_reminder", "not_due"]
    reminder: SimulatedReminderOut | None


class SimulatedReminderList(BaseModel):
    application_id: uuid.UUID
    items: list[SimulatedReminderOut]
    total: int
    limit: int
