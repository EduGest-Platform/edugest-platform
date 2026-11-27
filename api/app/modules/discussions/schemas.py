import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ThreadScope(BaseModel):
    model_config = ConfigDict(extra='forbid')
    scope_type: Literal['application', 'program']
    application_id: uuid.UUID | None = None
    program_id: str | None = Field(default=None, min_length=1, max_length=20)

    @model_validator(mode='after')
    def exact_scope(self):
        if self.scope_type == 'application' and (self.application_id is None or self.program_id is not None):
            raise ValueError('El hilo de expediente requiere solo application_id')
        if self.scope_type == 'program' and (self.program_id is None or self.application_id is not None):
            raise ValueError('El hilo de programa requiere solo program_id')
        return self


class ThreadCreate(ThreadScope):
    subject: str = Field(min_length=1, max_length=160)

    @field_validator('subject', mode='before')
    @classmethod
    def trim_subject(cls, value):
        return value.strip() if isinstance(value, str) else value


class ThreadOut(ThreadScope):
    id: uuid.UUID
    subject: str
    created_by: uuid.UUID
    created_at: datetime
    resolved_by: uuid.UUID | None
    resolved_at: datetime | None
    version: int


class DiscussionProgram(BaseModel):
    id: str
    name: str
    can_write: bool


class ThreadList(BaseModel):
    items: list[ThreadOut]
    total: int


class CommentCreate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    body: str = Field(min_length=1, max_length=2000, description='Texto plano interno; la interfaz debe renderizarlo escapado')
    parent_id: uuid.UUID | None = None

    @field_validator('body', mode='before')
    @classmethod
    def trim_body(cls, value):
        return value.strip() if isinstance(value, str) else value


class CommentEdit(BaseModel):
    model_config = ConfigDict(extra='forbid')
    body: str = Field(min_length=1, max_length=2000)
    expected_version: int = Field(ge=1)

    @field_validator('body', mode='before')
    @classmethod
    def trim_body(cls, value):
        return value.strip() if isinstance(value, str) else value


class VersionWrite(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: int = Field(ge=1)


class ResolutionWrite(VersionWrite):
    resolved: bool


class CommentOut(BaseModel):
    id: uuid.UUID
    thread_id: uuid.UUID
    parent_id: uuid.UUID | None
    actor_user_id: uuid.UUID
    body: str | None = Field(description='Nulo tras borrado lógico; no se expone el texto retenido')
    version: int
    created_at: datetime
    edited_at: datetime | None
    deleted_at: datetime | None


class CommentMutationOut(CommentOut):
    thread_version: int


class CommentList(BaseModel):
    items: list[CommentOut]
    total: int
