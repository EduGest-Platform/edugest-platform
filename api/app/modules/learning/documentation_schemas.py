import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DocumentationState = Literal['pending', 'accredited']


class DocumentationOut(BaseModel):
    enrollment_id: uuid.UUID
    state: DocumentationState
    version: int
    accredited_at: datetime | None


class DocumentationWrite(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: int = Field(strict=True, ge=1)


class DocumentationHistoryItem(BaseModel):
    version: int = Field(ge=2)
    state: DocumentationState
    recorded_at: datetime


class DocumentationHistory(BaseModel):
    enrollment_id: uuid.UUID
    items: list[DocumentationHistoryItem]
    total: int
