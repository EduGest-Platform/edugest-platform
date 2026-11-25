"""Competency framework versioning and assessments (KAN-57)."""

import uuid

from fastapi import status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core import audit
from app.core.authz import Principal, Scope
from app.core.db import utcnow
from app.core.errors import UserFacingError
from app.modules.catalog.models import Cohort, Program
from app.modules.competencies.models import CohortCompetencyFramework, Competency, CompetencyAssessment, CompetencyFramework
from app.modules.competencies.schemas import AssessmentWrite, CompetencyWrite, CurrentLevel
from app.modules.learning.access import cohort_scope
from app.modules.learning.models import Enrollment


def _conflict(code: str, message: str) -> UserFacingError:
    return UserFacingError(status.HTTP_409_CONFLICT, code, message)


# ---------- Access ----------


def require_program(db: Session, p: Principal, perm: str, program_id: str) -> Program:
    """A program's tree may be managed by whoever holds `perm` on the program or on any of its cohorts."""
    program = db.get(Program, program_id)
    if not program:
        raise UserFacingError(status.HTTP_404_NOT_FOUND, "program_not_found", "No encontramos este bootcamp. Vuelve a la lista de programas.")
    cohorts = db.scalars(select(Cohort).where(Cohort.program_id == program_id))
    if not (p.can(perm, Scope(program_id=program_id)) or any(p.can(perm, cohort_scope(c)) for c in cohorts)):
        p.require(perm, Scope(program_id=program_id))
    return program


def load_framework(db: Session, framework_id: uuid.UUID, lock: bool = False) -> CompetencyFramework:
    query = select(CompetencyFramework).where(CompetencyFramework.id == framework_id)
    framework = db.scalar(query.with_for_update() if lock else query)
    if not framework:
        raise UserFacingError(status.HTTP_404_NOT_FOUND, "framework_not_found", "No encontramos esta versión del árbol de competencias.")
    return framework


def competencies_of(db: Session, framework_id: uuid.UUID) -> list[Competency]:
    return list(db.scalars(select(Competency).where(Competency.framework_id == framework_id).order_by(Competency.orden)))


# ---------- Framework versions ----------


def _replace_competencies(db: Session, framework: CompetencyFramework, items: list[CompetencyWrite]) -> None:
    for old in competencies_of(db, framework.id):
        db.delete(old)
    db.flush()
    for order, item in enumerate(items, start=1):
        db.add(Competency(framework_id=framework.id, orden=order, **item.model_dump()))


def create_draft(db: Session, p: Principal, program: Program, items: list[CompetencyWrite]) -> CompetencyFramework:
    latest = db.scalar(select(func.max(CompetencyFramework.version)).where(CompetencyFramework.program_id == program.id)) or 0
    published = db.scalar(select(CompetencyFramework.id).where(CompetencyFramework.program_id == program.id, CompetencyFramework.estado == "publicada"))
    framework = CompetencyFramework(program_id=program.id, version=latest + 1, estado="borrador", based_on_id=published, created_by=p.user.id)
    db.add(framework)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise _conflict("framework_version_taken", "Otra persona acaba de crear una versión. Recarga y vuelve a intentarlo.") from None
    _replace_competencies(db, framework, items)
    audit.record(db, p, "competencies.framework_created", "competency_framework", str(framework.id), program_id=program.id, version=framework.version)
    db.commit()
    return framework


def update_draft(db: Session, p: Principal, framework: CompetencyFramework, items: list[CompetencyWrite]) -> CompetencyFramework:
    if framework.estado != "borrador":
        raise _conflict("framework_not_draft", "Esta versión ya está publicada y no se puede cambiar. Crea una versión nueva.")
    _replace_competencies(db, framework, items)
    audit.record(db, p, "competencies.framework_updated", "competency_framework", str(framework.id), version=framework.version, competencies=len(items))
    db.commit()
    return framework


def publish(db: Session, p: Principal, framework: CompetencyFramework) -> CompetencyFramework:
    """Freezes a draft and archives the previously published version of the same program (kept for traceability)."""
    if framework.estado != "borrador":
        raise _conflict("framework_not_draft", "Solo se puede publicar un borrador.")
    previous = db.scalar(
        select(CompetencyFramework).where(CompetencyFramework.program_id == framework.program_id, CompetencyFramework.estado == "publicada").with_for_update()
    )
    if previous:
        previous.estado = "archivada"
        db.flush()
    framework.estado, framework.published_at = "publicada", utcnow()
    audit.record(db, p, "competencies.framework_published", "competency_framework", str(framework.id),
                 version=framework.version, archived=str(previous.id) if previous else None)
    db.commit()
    return framework


def assign_to_cohort(db: Session, p: Principal, cohort: Cohort, framework: CompetencyFramework) -> None:
    if framework.program_id != cohort.program_id:
        raise _conflict("framework_other_program", "Este árbol es de otro bootcamp. Elige uno del programa de la cohorte.")
    if framework.estado != "publicada":
        raise _conflict("framework_not_published", "Solo se puede asignar la versión publicada del árbol.")
    link = db.get(CohortCompetencyFramework, cohort.id)
    previous = str(link.framework_id) if link else None
    if link:
        link.framework_id, link.assigned_by, link.assigned_at = framework.id, p.user.id, utcnow()
    else:
        db.add(CohortCompetencyFramework(cohort_id=cohort.id, framework_id=framework.id, assigned_by=p.user.id))
    audit.record(db, p, "competencies.cohort_framework_assigned", "cohort", cohort.id, framework_id=str(framework.id), previous=previous)
    db.commit()


def cohort_framework(db: Session, cohort_id: str) -> CompetencyFramework | None:
    link = db.get(CohortCompetencyFramework, cohort_id)
    return db.get(CompetencyFramework, link.framework_id) if link else None


# ---------- Assessments ----------


def current_enrollment_levels(db: Session, enrollment_id: uuid.UUID, framework_id: uuid.UUID) -> list[CurrentLevel]:
    competencies = competencies_of(db, framework_id)
    if not competencies:
        return []
    assessment = CompetencyAssessment
    rows = db.execute(
        select(assessment.competency_id, assessment.level, assessment.assessed_at)
        .where(assessment.enrollment_id == enrollment_id, assessment.competency_id.in_([c.id for c in competencies]))
        .order_by(assessment.assessed_at, assessment.id)
    )
    latest = {row.competency_id: row for row in rows}
    levels = []
    for competency in competencies:
        evaluation = latest.get(competency.id)
        levels.append(CurrentLevel(
            competency_id=competency.id,
            codigo=competency.codigo,
            nombre=competency.nombre,
            level=evaluation.level if evaluation else None,
            assessed_at=evaluation.assessed_at if evaluation else None,
        ))
    return levels


def assess(db: Session, p: Principal, enrollment: Enrollment, body: AssessmentWrite) -> CompetencyAssessment:
    """Only competencies of the cohort's own framework can be assessed, so other courses' trees never leak in."""
    framework = cohort_framework(db, enrollment.cohort_id)
    competency = db.get(Competency, body.competency_id)
    if framework is None or competency is None or competency.framework_id != framework.id:
        raise _conflict("competency_not_in_cohort", "Esta competencia no pertenece al árbol que usa la cohorte. Recarga la lista de competencias.")
    assessment = CompetencyAssessment(
        enrollment_id=enrollment.id, competency_id=competency.id, level=body.level, evidence=body.evidence, assessed_by=p.user.id
    )
    db.add(assessment)
    db.flush()
    audit.record(db, p, "competencies.assessed", "enrollment", str(enrollment.id), competency=competency.codigo, level=body.level)
    db.commit()
    return assessment
