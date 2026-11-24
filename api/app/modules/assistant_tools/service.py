"""KAN-263: computations behind the read-only assistant tools. Plain queries, no AI, scope checked by the caller."""

import uuid
from collections import Counter
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.authz import Principal
from app.core.config import settings
from app.modules.assistant_tools.schemas import (
    AssignmentStatus,
    CompetencyDistribution,
    CompetencyProgress,
    EnrollmentPending,
    EnrollmentProgress,
    LevelCount,
    PendingSubmissions,
    StateCount,
)
from app.modules.catalog.models import Cohort
from app.modules.competencies.models import Competency, CompetencyAssessment
from app.modules.competencies.service import cohort_framework
from app.modules.learning.access import cohort_scope, load_cohort
from app.modules.learning.models import Enrollment
from app.modules.submissions.models import Assignment, Submission
from app.modules.submissions.service import delivery_state, published_assignments


def cohort_access(db: Session, p: Principal, cohort_id: str, read_perm: str, aggregate_perm: str) -> tuple[Cohort, bool]:
    """Returns the cohort and whether per-enrollment rows may be shown. Aggregate-only roles get totals; others 403."""
    cohort = load_cohort(db, cohort_id)
    if p.can(read_perm, cohort_scope(cohort)):
        return cohort, True
    p.require(aggregate_perm, cohort_scope(cohort))
    return cohort, False


def enrollment_ids_of(db: Session, cohort_id: str) -> list[uuid.UUID]:
    """Active enrollments only (KAN-158): coders who left or finished are never pending, overdue or counted in totals."""
    query = (
        select(Enrollment.id)
        .where(Enrollment.cohort_id == cohort_id, Enrollment.estado == "activa")
        .order_by(Enrollment.created_at, Enrollment.id)
    )
    return list(db.scalars(query))


def group_too_small(enrollment_count: int) -> bool:
    """Same k-anonymity threshold as the attendance totals: small groups are never shown in aggregate."""
    return enrollment_count < settings.min_group_size


# ---------- get_competency_progress ----------


def competency_progress(db: Session, cohort_id: str, per_person: bool) -> tuple[CompetencyProgress, bool]:
    """Current level per coder and competency (latest assessment wins) and the 1/2/3/not assessed distribution."""
    framework = cohort_framework(db, cohort_id)
    enrollments = enrollment_ids_of(db, cohort_id)
    suppressed = group_too_small(len(enrollments))
    if framework is None:
        empty = CompetencyProgress(framework_version=None, suppressed=suppressed, min_group_size=settings.min_group_size, distribution=[], items=[])
        return empty, False
    competencies = list(db.scalars(select(Competency).where(Competency.framework_id == framework.id).order_by(Competency.orden)))
    current = _current_levels(db, enrollments, [c.id for c in competencies])
    distribution = [
        CompetencyDistribution(codigo=c.codigo, nombre=c.nombre, counts=None if suppressed else _level_count(current, enrollments, c.id))
        for c in competencies
    ]
    items = [
        EnrollmentProgress(enrollment_id=e, levels={c.codigo: current.get((e, c.id)) for c in competencies}) for e in enrollments
    ] if per_person else []
    progress = CompetencyProgress(framework_version=framework.version, suppressed=suppressed, min_group_size=settings.min_group_size,
                                  distribution=distribution, items=items)
    return progress, bool(current)


def _current_levels(db: Session, enrollments: list[uuid.UUID], competency_ids: list[uuid.UUID]) -> dict[tuple[uuid.UUID, uuid.UUID], int]:
    if not enrollments or not competency_ids:
        return {}
    query = (
        select(CompetencyAssessment)
        .where(CompetencyAssessment.enrollment_id.in_(enrollments), CompetencyAssessment.competency_id.in_(competency_ids))
        .order_by(CompetencyAssessment.assessed_at, CompetencyAssessment.id)
    )
    return {(a.enrollment_id, a.competency_id): a.level for a in db.scalars(query)}  # chronological: the last one wins


def _level_count(current: dict, enrollments: list[uuid.UUID], competency_id: uuid.UUID) -> LevelCount:
    levels = Counter(current.get((e, competency_id)) for e in enrollments)
    return LevelCount(level_1=levels[1], level_2=levels[2], level_3=levels[3], not_assessed=levels[None])


# ---------- get_pending_submissions ----------


def pending_submissions(db: Session, cohort: Cohort, per_person: bool, now: datetime) -> tuple[PendingSubmissions, bool]:
    assignments = published_assignments(db, cohort.id)
    enrollments = enrollment_ids_of(db, cohort.id)
    suppressed = group_too_small(len(enrollments))
    submissions = _submissions_of(db, assignments)
    states = {
        (e, a.id): delivery_state(a, submissions.get((e, a.id)), now) for a in assignments for e in enrollments
    }
    summary = [
        AssignmentStatus(assignment_id=a.id, title=a.title, due_at=a.due_at,
                         counts=None if suppressed else _state_count(states, submissions, enrollments, a.id))
        for a in assignments
    ]
    items = [
        EnrollmentPending(enrollment_id=e, states={str(a.id): states[(e, a.id)] for a in assignments}) for e in enrollments
    ] if per_person else []
    result = PendingSubmissions(timezone=cohort.timezone, suppressed=suppressed, min_group_size=settings.min_group_size,
                                assignments=summary, items=items)
    return result, bool(assignments and enrollments)


def _submissions_of(db: Session, assignments: list[Assignment]) -> dict[tuple[uuid.UUID, uuid.UUID], Submission]:
    ids = [a.id for a in assignments]
    if not ids:
        return {}
    return {(s.enrollment_id, s.assignment_id): s for s in db.scalars(select(Submission).where(Submission.assignment_id.in_(ids)))}


def _state_count(states: dict, submissions: dict, enrollments: list[uuid.UUID], assignment_id: uuid.UUID) -> StateCount:
    counted = Counter(states[(e, assignment_id)] for e in enrollments)
    reviewed = sum(1 for e in enrollments if (s := submissions.get((e, assignment_id))) and s.status == "reviewed")
    return StateCount(on_time=counted["on_time"], late=counted["late"], pending=counted["pending"], overdue=counted["overdue"], reviewed=reviewed)

