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
    expected_version: int = Field(ge=1)
