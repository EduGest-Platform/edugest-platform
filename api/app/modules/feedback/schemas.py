import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FeedbackDraftOut(BaseModel):
    """One version as the teaching team sees it. No user ids: who wrote and approved it stays in the database and audit."""

    id: uuid.UUID
    submission_id: uuid.UUID
    submission_revision: int = Field(description="Revisión de la entrega a la que corresponde este borrador")
    version: int
    source: Literal["template", "teacher"] = Field(
        description="template = generado automáticamente con la rúbrica y los tests (sin LLM); teacher = editado por el docente")
    status: Literal["draft", "approved"] = Field(description="draft = no visible para el coder; approved = publicado")
    label: str = Field(description="Texto que la interfaz debe mostrar junto al borrador")
    body: str
    rubric: list[str] = Field(description="Copia de la rúbrica usada (procedencia)")
    check_results: dict = Field(description="Copia de los resultados de tests usados (procedencia)")
    created_at: datetime
    approved_at: datetime | None


class FeedbackDraftList(BaseModel):
    submission_id: uuid.UUID
    current_revision: int = Field(description="Revisión actual de la entrega")
    items: list[FeedbackDraftOut] = Field(description="Todas las versiones, de la más antigua a la más reciente")


class DraftEdit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str = Field(min_length=1, max_length=4000, description="Texto revisado por el docente")
    expected_version: int = Field(ge=1, description="Versión que el docente estaba editando (evita pisar cambios ajenos)")

    @field_validator("body", mode="before")
    @classmethod
    def _trim(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class ApproveIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(ge=1, description="Revisión de la entrega que el docente ha visto")


class PublishedFeedbackOut(BaseModel):
    version: int
    label: str
    body: str
    approved_at: datetime


class PublishedFeedback(BaseModel):
    """What the coder sees: only approved feedback, never drafts."""

    submission_id: uuid.UUID
    feedback: PublishedFeedbackOut | None = Field(description="Nulo si todavía no hay feedback aprobado")
