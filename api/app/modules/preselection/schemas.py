import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Decision = Literal["convocada", "retirada_expresa", "silencio_confirmado", "silencio_reprogramado"]


class PreselectionDecisionWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Decision
    reason: str = Field(min_length=1, max_length=500, description="Motivo operativo. No incluir datos de salud ni situación personal.")

    @field_validator("reason", mode="before")
    @classmethod
    def _trim_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class SilenceEvidence(BaseModel):
    """Why an application is (or is not) pending a silence review. Computed from CRM contacts, never stored as a state."""

    unanswered_attempts: int
    last_attempt_at: datetime | None
    days_without_response: int | None
    silence_days: int
    silence_max_contacts: int
    threshold_met: bool


class PreselectionDecisionOut(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    decision: Decision
    from_stage: str
    to_stage: str
    reason: str
    actor: str | None
    occurred_at: datetime
    evidence: dict


class PreselectionDecisionList(BaseModel):
    application_id: uuid.UUID
    items: list[PreselectionDecisionOut]


class SilenceReviewItem(BaseModel):
    application_id: uuid.UUID
    codigo: str
    stage: str
    evidence: SilenceEvidence


class SilenceReviewList(BaseModel):
    call_id: str
    items: list[SilenceReviewItem]


class PreselectionPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    silence_days: int = Field(ge=1, le=365, description="Días sin respuesta tras el último intento antes de proponer revisión de silencio")
    silence_max_contacts: int = Field(ge=1, le=20, description="Intentos de contacto sin respuesta registrados antes de proponer revisión de silencio")
