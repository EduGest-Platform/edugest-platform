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


class SelectionApprovalOut(BaseModel):
    decision: Decision
    cohort_id: str | None
    reason: str
    actor: str | None
    occurred_at: datetime


class SelectionPendingOut(BaseModel):
    """Returned with 202 when the vote was recorded but fewer than `quorum` different people agree yet."""

    application_id: uuid.UUID
    state: Literal["pending", "disagreement"] = Field(description="pending: falta otra persona; disagreement: hay votos distintos")
    stage: str
    quorum: int = Field(description="Personas distintas que deben coincidir (configurable por convocatoria, por defecto 2)")
    votes: list[SelectionApprovalOut]


class SelectionDecisionList(BaseModel):
    application_id: uuid.UUID
    items: list[SelectionDecisionOut]
    quorum: int = Field(description="Personas distintas que deben coincidir en esta convocatoria")
    pending_votes: list[SelectionApprovalOut] = Field(description="Votos que aún no han alcanzado el quórum")


# Provisional rule until the foundation confirms the priority criteria (review of PR #95, point 2).
WAITING_ORDER_BASIS = "entrada_en_lista"


class SelectionCandidate(BaseModel):
    """An application still in selection, shown next to the places of the call so the team deliberates comparatively."""

    application_id: uuid.UUID
    codigo: str
    stage: str
    stage_label: str


class WaitingListEntry(BaseModel):
    position: int = Field(ge=1, description="Lugar en la lista según el criterio provisional (orden de entrada en la lista)")
    application_id: uuid.UUID
    codigo: str
    since: datetime = Field(description="Cuándo entró en la lista de espera")
    is_next: bool = Field(description="Primera de la lista: es la que se propone si se libera una plaza. Una persona decide siempre.")


class SelectionOverview(BaseModel):
    call_id: str
    plazas: int
    admitted: int
    free_places: int = Field(description="Plazas sin cubrir (nunca negativo)")
    in_selection: int
    waiting: int
    candidates: list[SelectionCandidate]
    waiting_list: list[WaitingListEntry]
    waiting_order_basis: Literal["entrada_en_lista"] = Field(
        description="Criterio con el que se ordena la lista de espera. Provisional: la fundación aún no ha confirmado los criterios de prioridad."
    )
    waiting_order_confirmed: bool = Field(description="False mientras la fundación no confirme el criterio de prioridad")


class SelectionPolicy(BaseModel):
    """Per-call selection rule. Melissa round 3 Q11: two approvals by default; administration may change it, audited."""

    model_config = ConfigDict(extra="forbid")

    selection_quorum: int = Field(ge=1, le=5, description="Personas distintas que deben coincidir en la decisión de selección (por defecto 2)")
