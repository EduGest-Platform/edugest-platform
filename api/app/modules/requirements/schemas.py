import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

ReviewResult = Literal["pending", "met", "not_met", "exception_under_review", "exception_approved"]
# «pending» is the state before any review: it cannot be written.
WritableResult = Literal["met", "not_met", "exception_under_review", "exception_approved"]

REQUIREMENT_REF_PATTERN = r"^[a-z0-9][a-z0-9_-]{0,59}$"


class CallRequirementWrite(BaseModel):
    """A fresh immutable reference, or the next version of the same logical code."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    ref: str = Field(pattern=REQUIREMENT_REF_PATTERN)
    code: str = Field(pattern=REQUIREMENT_REF_PATTERN)
    label: str = Field(min_length=1, max_length=200)
    kind: Literal["required", "recommended"]
    funder: str | None = Field(None, min_length=1, max_length=120)
    expected_version: int = Field(0, ge=0, description="0 para un código nuevo; versión anterior al publicar su sucesora")


class CallRequirementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    call_id: str
    ref: str
    code: str
    version: int
    label: str
    kind: Literal["required", "recommended"]
    funder: str | None
    created_at: datetime


class CallRequirementList(BaseModel):
    call_id: str
    items: list[CallRequirementOut]


class RequirementReviewWrite(BaseModel):
    """Body to record or revise a review. Author and date are never accepted from the client."""

    model_config = ConfigDict(extra="forbid")

    result: WritableResult
    reason: str = Field(
        min_length=1,
        max_length=500,
        description="Motivo operativo. No incluir datos de salud, situación personal ni otros datos sensibles.",
    )
    expected_version: int | None = Field(
        None, ge=1, description="Versión que la persona vio al abrir la revisión. Se omite solo al crear la primera."
    )

    @field_validator("reason", mode="before")
    @classmethod
    def _strip_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class RequirementReviewOut(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    requirement_ref: str
    requirement_definition_id: uuid.UUID | None = None
    result: ReviewResult
    reviewer: str | None
    reviewed_at: datetime | None
    reason: str | None
    version: int


class RequirementReviewList(BaseModel):
    """An empty list means «not reviewed yet», never «all requirements met»."""

    application_id: uuid.UUID
    items: list[RequirementReviewOut]


class RequirementRevisionOut(BaseModel):
    revision: int
    requirement_definition_id: uuid.UUID | None = None
    result: ReviewResult
    reviewer: str | None
    reviewed_at: datetime
    reason: str


class RequirementReviewHistory(BaseModel):
    review_id: uuid.UUID
    requirement_ref: str
    items: list[RequirementRevisionOut]
