from datetime import date

from pydantic import BaseModel


class CallOut(BaseModel):
    id: str
    program_id: str
    program_nombre: str
    nombre: str
    opens_on: date
    closes_on: date
    plazas: int
    estado: str


class StageCount(BaseModel):
    stage: str
    # None when suppressed (small cell) to avoid re-identification.
    count: int | None
    suppressed: bool


class CallSummaryOut(BaseModel):
    call_id: str
    total: int | None
    suppressed: bool
    min_group_size: int
    min_cell_size: int
    by_stage: list[StageCount]
