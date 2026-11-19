import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

FrameworkState = Literal["borrador", "publicada", "archivada"]
Level = Literal[1, 2, 3]


def _strip(value: object) -> object:
    return value.strip() if isinstance(value, str) else value


class CompetencyWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    codigo: str = Field(pattern=r"^C[1-9][0-9]?$", description="C1, C2… como en el briefing")
    nombre: str = Field(min_length=1, max_length=160)
    descripcion: str = Field(default="", max_length=2000)
    level_1: str = Field(min_length=1, max_length=2000, description="Qué demuestra un coder en el nivel 1")
    level_2: str = Field(min_length=1, max_length=2000)
    level_3: str = Field(min_length=1, max_length=2000)

    @field_validator("codigo", "nombre", "descripcion", "level_1", "level_2", "level_3", mode="before")
    @classmethod
    def _trim(cls, value: object) -> object:
        return _strip(value)


class FrameworkWrite(BaseModel):
    """The full list of competencies of a draft version. Order in the list is the display order."""

    model_config = ConfigDict(extra="forbid")

    competencies: list[CompetencyWrite] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def _unique_codes(self) -> "FrameworkWrite":
        codes = [c.codigo for c in self.competencies]
        if len(codes) != len(set(codes)):
            raise ValueError("Cada código de competencia debe aparecer una sola vez")
        return self


class CompetencyOut(BaseModel):
    id: uuid.UUID
    codigo: str
    nombre: str
    descripcion: str
    level_1: str
    level_2: str
    level_3: str
    orden: int


class FrameworkOut(BaseModel):
    id: uuid.UUID
    program_id: str
    version: int
    estado: FrameworkState
    created_at: datetime
    published_at: datetime | None
    competencies: list[CompetencyOut]


class FrameworkList(BaseModel):
    program_id: str
    items: list[FrameworkOut]


class CohortFrameworkWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    framework_id: uuid.UUID


class CohortCompetencies(BaseModel):
    cohort_id: str
    framework: FrameworkOut | None = Field(description="Versión del árbol que usa la cohorte. Nulo si aún no tiene ninguna")


class AssessmentWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    competency_id: uuid.UUID
    level: Level
    evidence: str = Field(min_length=1, max_length=500, description="En qué se basa el nivel (entrega, observación…). Sin datos personales.")

    @field_validator("evidence", mode="before")
    @classmethod
    def _trim(cls, value: object) -> object:
        return _strip(value)


class AssessmentOut(BaseModel):
    id: uuid.UUID
    enrollment_id: uuid.UUID
    competency_id: uuid.UUID
    codigo: str
    framework_version: int
    level: Level
    evidence: str
    assessed_by: str | None
    assessed_at: datetime


class CurrentLevel(BaseModel):
    competency_id: uuid.UUID
    codigo: str
    nombre: str
    level: Level | None = Field(description="Último nivel evaluado. Nulo = sin evaluar (nunca nivel 0)")
    assessed_at: datetime | None


class EnrollmentAssessments(BaseModel):
    enrollment_id: uuid.UUID
    framework_version: int | None
    current: list[CurrentLevel]
    history: list[AssessmentOut] = Field(description="Todas las evaluaciones, también de versiones anteriores del árbol")
