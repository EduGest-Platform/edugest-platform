"""KAN-263: allowlisted read-only endpoints for the assistant tools (KAN-158, KAN-262, KAN-191).

The assistant calls these with the user's own token: FastAPI decides the scope before any query, the model never
writes SQL and never picks its own scope. Every response uses the ToolResponse envelope.
"""

import uuid
from datetime import date

from fastapi import APIRouter, Query

from app.core import audit
from app.core.db import utcnow
from app.core.deps import DB, CurrentPrincipal
from app.modules.assistant_tools.schemas import (
    AttendanceToolResponse,
    CompetencyToolResponse,
    PendingToolResponse,
    SubmissionContext,
    SubmissionToolResponse,
    ToolPeriod,
    ToolScope,
)
from app.modules.assistant_tools.service import cohort_access, competency_progress, pending_submissions
from app.modules.attendance.router import get_attendance_summary
from app.modules.submissions.schemas import DELIVERY_RULE, CheckResults
from app.modules.submissions.service import delivery_state, load_assignment, load_submission
from app.modules.learning.access import cohort_scope, load_cohort, require_cohort

router = APIRouter(prefix="/tools", tags=["assistant-tools"])

_ERRORS = {403: {"description": "Sin permiso sobre la cohorte"}, 404: {"description": "No encontrado"}}
COMPETENCY_RULE = "Nivel actual = última evaluación docente (1–3) en la versión del árbol asignada a la cohorte. Sin evaluación = sin evaluar, nunca 0."
NO_PERIOD = ToolPeriod(date_from=None, date_to=None)
CohortQuery = Query(max_length=20, description="Cohorte consultada")


@router.get("/attendance-summary", response_model=AttendanceToolResponse, responses=_ERRORS,
            summary="Herramienta get_attendance_summary: totales de asistencia con periodo y regla")
def tool_attendance_summary(p: CurrentPrincipal, db: DB, cohort_id: str = CohortQuery, enrollment_id: uuid.UUID | None = None,
                            date_from: date | None = None, date_to: date | None = None) -> AttendanceToolResponse:
    summary = get_attendance_summary(p, db, cohort_id=cohort_id, enrollment_id=enrollment_id, date_from=date_from, date_to=date_to)
    per_person = p.can("attendance.read", cohort_scope(load_cohort(db, cohort_id)))
    recorded = any(item.held_days > item.unrecorded_days for item in summary.items)
    has_data = recorded or summary.cohort_totals.attendance_rate is not None
    return AttendanceToolResponse(
        tool="get_attendance_summary", scope=ToolScope(cohort_id=cohort_id, enrollment_id=enrollment_id),
        period=ToolPeriod(date_from=date_from, date_to=date_to), generated_at=utcnow(),
        source="attendance_session, attendance_record", rule=summary.rule, aggregate_only=not per_person,
        has_data=has_data, data=summary,
    )


@router.get("/competency-progress", response_model=CompetencyToolResponse, responses=_ERRORS,
            summary="Herramienta get_competency_progress: nivel actual por competencia y reparto 1/2/3")
def tool_competency_progress(p: CurrentPrincipal, db: DB, cohort_id: str = CohortQuery) -> CompetencyToolResponse:
    cohort, per_person = cohort_access(db, p, cohort_id, "competencies.read", "competencies.aggregate")
    progress, has_data = competency_progress(db, cohort.id, per_person)
    audit.record(db, p, "tools.competency_progress", "cohort", cohort.id, per_enrollment=per_person)
    db.commit()
    return CompetencyToolResponse(
        tool="get_competency_progress", scope=ToolScope(cohort_id=cohort.id), period=NO_PERIOD, generated_at=utcnow(),
        source="competency_framework, competency, competency_assessment", rule=COMPETENCY_RULE,
        aggregate_only=not per_person, has_data=has_data, data=progress,
    )


@router.get("/pending-submissions", response_model=PendingToolResponse, responses=_ERRORS,
            summary="Herramienta get_pending_submissions: estado de entregas por actividad")
def tool_pending_submissions(p: CurrentPrincipal, db: DB, cohort_id: str = CohortQuery) -> PendingToolResponse:
    cohort, per_person = cohort_access(db, p, cohort_id, "submissions.read", "submissions.aggregate")
    now = utcnow()
    result, has_data = pending_submissions(db, cohort, per_person, now)
    audit.record(db, p, "tools.pending_submissions", "cohort", cohort.id, per_enrollment=per_person)
    db.commit()
    return PendingToolResponse(
        tool="get_pending_submissions", scope=ToolScope(cohort_id=cohort.id), period=ToolPeriod(date_from=None, date_to=now.date()),
        generated_at=now, source="assignment, submission", rule=DELIVERY_RULE, aggregate_only=not per_person, has_data=has_data, data=result,
    )


@router.get("/submissions/{submission_id}", response_model=SubmissionToolResponse, responses=_ERRORS,
            summary="Herramienta get_submission_context: rúbrica y tests precalculados para un borrador de feedback (sin URL ni contenido)")
def tool_submission_context(submission_id: uuid.UUID, p: CurrentPrincipal, db: DB) -> SubmissionToolResponse:
    submission = load_submission(db, submission_id)
    assignment = load_assignment(db, submission.assignment_id)
    require_cohort(db, p, "submissions.review", assignment.cohort_id)
    now = utcnow()
    context = SubmissionContext(
        submission_id=submission.id, assignment_title=assignment.title, rubric=list(assignment.rubric or []), due_at=assignment.due_at,
        state=delivery_state(assignment, submission, now), reviewed=submission.status == "reviewed", revision=submission.revision,
        check_results=CheckResults(**submission.check_results) if submission.check_results else None,
    )
    audit.record(db, p, "tools.submission_context", "submission", str(submission.id))
    db.commit()
    return SubmissionToolResponse(
        tool="get_submission_context", scope=ToolScope(cohort_id=assignment.cohort_id, enrollment_id=submission.enrollment_id),
        period=NO_PERIOD, generated_at=now, source="assignment, submission", rule=DELIVERY_RULE, aggregate_only=False,
        has_data=True, data=context,
    )
