"""KAN-263: one envelope for every read-only assistant tool (AGENTS.md §4, ADR-0005).

Every answer says who it covers (scope), over which period, how fresh it is, where it comes from and which rule
was applied. has_data = false means "abstain": the assistant must say there is no data, never invent zeros.
No names or e-mails ever: people are identified only by enrollment_id.
"""

import uuid
from datetime import date, datetime
from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field

from app.modules.attendance.schemas import AttendanceSummary
from app.modules.submissions.schemas import CheckResults, DeliveryState

T = TypeVar("T")
COMPETENCY_RULE = "Nivel actual = última evaluación docente (1–3) en la versión del árbol asignada a la cohorte. Sin evaluación = sin evaluar, nunca 0."


class ToolScope(BaseModel):
    cohort_id: str
    enrollment_id: uuid.UUID | None = None


class ToolPeriod(BaseModel):
    date_from: date | None = Field(description="Inicio del periodo; nulo = desde el inicio de la cohorte")
    date_to: date | None = Field(description="Fin del periodo; nulo = hasta hoy")


class ToolResponse(BaseModel, Generic[T]):
    tool: str
    scope: ToolScope
    period: ToolPeriod
    generated_at: datetime = Field(description="Momento de la consulta: los datos son de este instante")
    source: str = Field(description="Tablas de origen")
    rule: str = Field(description="Regla de cálculo que debe citar el asistente")
    aggregate_only: bool = Field(description="Verdadero si el rol solo puede ver totales (coordinación)")
    has_data: bool = Field(description="Falso = abstenerse; no hay datos, no son ceros")
    data: T


# ---------- get_competency_progress ----------


class LevelCount(BaseModel):
    level_1: int
    level_2: int
    level_3: int
    not_assessed: int


class CompetencyDistribution(BaseModel):
    codigo: str
    nombre: str
    counts: LevelCount | None = Field(description="Nulo si el grupo es demasiado pequeño para mostrarlo")


class EnrollmentProgress(BaseModel):
    enrollment_id: uuid.UUID
    levels: dict[str, int | None] = Field(description="Nivel actual 1–3 por código de competencia; nulo = sin evaluar")


class CompetencyProgress(BaseModel):
    framework_version: int | None
    suppressed: bool
    min_group_size: int
    distribution: list[CompetencyDistribution]
    items: list[EnrollmentProgress] = Field(description="Vacío para coordinación")


# ---------- get_pending_submissions ----------


class StateCount(BaseModel):
    on_time: int
    late: int
    pending: int
    overdue: int
    reviewed: int


class AssignmentStatus(BaseModel):
    assignment_id: uuid.UUID
    title: str
    due_at: datetime
    counts: StateCount | None = Field(description="Nulo si el grupo es demasiado pequeño para mostrarlo")


class EnrollmentPending(BaseModel):
    enrollment_id: uuid.UUID
    states: dict[str, DeliveryState] = Field(description="Estado por assignment_id")


class PendingSubmissions(BaseModel):
    timezone: str
    suppressed: bool
    min_group_size: int
    assignments: list[AssignmentStatus]
    items: list[EnrollmentPending] = Field(description="Vacío para coordinación")


# ---------- get_submission_context (KAN-191) ----------


class SubmissionContext(BaseModel):
    """What a feedback draft may use. Never the portfolio URL or any submitted content (privacy, PO 23/11/2026)."""

    submission_id: uuid.UUID
    assignment_title: str
    rubric: list[str]
    due_at: datetime
    state: DeliveryState
    reviewed: bool
    revision: int = Field(description="Versión de la entrega a la que corresponden check_results")
    check_results: CheckResults | None


AttendanceToolResponse = ToolResponse[AttendanceSummary]
CompetencyToolResponse = ToolResponse[CompetencyProgress]
PendingToolResponse = ToolResponse[PendingSubmissions]
SubmissionToolResponse = ToolResponse[SubmissionContext]
ToolName = Literal["get_attendance_summary", "get_competency_progress", "get_pending_submissions", "get_submission_context"]
