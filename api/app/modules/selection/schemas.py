import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Decision = Literal["admitida", "lista_espera", "no_admitida"]


class SelectionDecisionWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Decision
    reason: str = Field(min_length=1, max_length=500, description="Motivo operativo. No incluir datos de salud ni situación personal.")
    cohort_id: str | None = Field(
        default=None, max_length=20,
        description="Cohorte en la que se matricula. Obligatoria al admitir y no permitida en las demás decisiones.",
    )

    @field_validator("reason", mode="before")
    @classmethod
    def _trim_reason(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def _cohort_only_when_admitting(self) -> "SelectionDecisionWrite":
        if self.decision == "admitida" and not self.cohort_id:
            raise ValueError("Para admitir hay que indicar la cohorte en la que se matricula")
        if self.decision != "admitida" and self.cohort_id:
            raise ValueError("Solo la admisión indica cohorte: no se matricula a nadie con esta decisión")
        return self


class SelectionDecisionOut(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    decision: Decision
    from_stage: str
    to_stage: str
    reason: str
    actor: str | None
    occurred_at: datetime
    cohort_id: str | None = Field(description="Cohorte de la matrícula creada (solo al admitir)")
    enrollment_id: uuid.UUID | None = Field(description="Matrícula creada por la decisión (solo al admitir)")


class SelectionDecisionList(BaseModel):
    application_id: uuid.UUID
    items: list[SelectionDecisionOut]
