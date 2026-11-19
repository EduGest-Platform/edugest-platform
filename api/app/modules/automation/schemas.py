import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.modules.requirements.schemas import PrefilterResult


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
    snapshot: PrefilterResult
    evaluated_at: datetime


class AutomationExecutionList(BaseModel):
    application_id: uuid.UUID
    items: list[AutomationExecutionOut]
    total: int
    limit: int
