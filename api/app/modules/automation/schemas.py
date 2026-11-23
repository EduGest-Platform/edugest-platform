import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, AwareDatetime, ConfigDict, Field, JsonValue, field_validator


from app.modules.knowledge.privacy import find_personal_data


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
    task_ref: str = Field(
        min_length=11, max_length=80, pattern=r"^synthetic-[a-z][a-z0-9]*(?:-[a-z0-9]+)*$",
        description="Referencia técnica sintética, p. ej. synthetic-docs-v1. No incluir nombres, teléfonos ni documentos personales.",
    )
    kind: Literal["documentation", "exercises"]
    due_at: AwareDatetime
    synthetic_only: Literal[True]

    @field_validator("task_ref")
    @classmethod
    def _technical_reference(cls, value: str) -> str:
        # Detect separated phone/document shapes too; long numeric runs are not technical demo labels.
        if re.search(r"\d{7,}", value) or find_personal_data(value.replace("-", " ")):
            raise ValueError("Usa una referencia técnica sintética sin teléfonos ni documentos personales")
        return value


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
