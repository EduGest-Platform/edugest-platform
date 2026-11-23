from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AskIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=3, max_length=500, description="Pregunta sobre la documentación del curso")
    cohort_id: str | None = Field(default=None, max_length=20, description="Opcional: busca solo en una de tus cohortes")

    @field_validator("question", mode="before")
    @classmethod
    def _trim(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value


class Citation(BaseModel):
    source_key: str
    title: str
    version: str
    valid_from: date
    valid_until: date | None
    excerpt: str


class AskOut(BaseModel):
    status: Literal["answered", "no_source"] = Field(description="no_source = abstención: no hay fuente en tu ámbito")
    mode: Literal["extractive"] = Field(description="extractive = fragmento literal del documento (el modo generated llega con T10)")
    retrieval: Literal["hybrid", "keyword"] = Field(description="hybrid = palabras y significado; keyword = solo palabras")
    answer: str
    citations: list[Citation]
    as_of: date = Field(description="Fecha de corte: la vigencia de los documentos se comprueba en esta fecha")
    scope_cohorts: list[str] = Field(description="Cohortes en las que se ha buscado")
