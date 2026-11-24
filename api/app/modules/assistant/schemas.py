from datetime import date, datetime
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


class RecordSource(BaseModel):
    tool: str = Field(description="Herramienta de solo lectura usada (get_attendance_summary, get_pending_submissions, get_competency_progress)")
    source: str = Field(description="Tablas de origen")
    rule: str = Field(description="Regla de cálculo aplicada")
    generated_at: datetime = Field(description="Momento de la consulta: los datos son de este instante")
    aggregate_only: bool = Field(description="Verdadero si el rol solo puede ver totales")


class AskOut(BaseModel):
    status: Literal["answered", "no_source"] = Field(description="no_source = abstención: no hay fuente o no hay registros")
    mode: Literal["extractive", "template"] = Field(
        description="extractive = fragmento literal del documento; template = frase fija con los totales de una herramienta")
    retrieval: Literal["hybrid", "keyword"] | None = Field(
        description="hybrid = palabras y significado; keyword = solo palabras; nulo si la respuesta sale de registros")
    answer: str
    citations: list[Citation]
    as_of: date = Field(description="Fecha de corte: la vigencia de los documentos se comprueba en esta fecha")
    scope_cohorts: list[str] = Field(description="Cohortes en las que se ha buscado")
    source_kind: Literal["documents", "records"] = Field(
        default="documents", description="documents = documentos del curso; records = registros operativos actuales")
    record: RecordSource | None = Field(
        default=None, description="Solo si source_kind = records: herramienta, fuente, regla y momento de la consulta")
