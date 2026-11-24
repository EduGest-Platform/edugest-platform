from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PublicationState = Literal['draft', 'published']


class PublicationUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    state: PublicationState
    expected_version: int = Field(ge=1)


class PublicationOut(BaseModel):
    call_id: str
    state: PublicationState
    version: int


class PublicCourseOut(BaseModel):
    """Explicit public projection; never serialize the entire Call or Program object."""
    id: str
    program_id: str
    program_name: str
    name: str
    opens_on: date
    closes_on: date
    capacity: int
    admission_state: Literal['abierta', 'cerrada']


class PublicCourseList(BaseModel):
    items: list[PublicCourseOut]
    total: int
