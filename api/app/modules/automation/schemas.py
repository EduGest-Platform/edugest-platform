import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, JsonValue


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
