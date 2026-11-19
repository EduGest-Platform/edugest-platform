import uuid

from fastapi import APIRouter, Path
from sqlalchemy import select

from app.core.deps import DB, CurrentPrincipal
from app.modules.competencies.models import Competency, CompetencyAssessment, CompetencyFramework
from app.modules.competencies.schemas import (
    AssessmentOut,
    AssessmentWrite,
    CohortCompetencies,
    CohortFrameworkWrite,
    CompetencyOut,
    CurrentLevel,
    EnrollmentAssessments,
    FrameworkList,
    FrameworkOut,
    FrameworkWrite,
)
from app.modules.competencies.service import (
    assess,
    assign_to_cohort,
    cohort_framework,
    competencies_of,
    create_draft,
    load_framework,
    publish,
    require_program,
    update_draft,
)
from app.modules.identity.models import User
from app.modules.learning.access import require_cohort, require_enrollment

router = APIRouter(tags=["competencies"])

ProgramId = Path(max_length=20)
CohortId = Path(max_length=20)
_ERRORS = {403: {"description": "Sin permiso sobre el ámbito"}, 404: {"description": "No encontrado"}}
_CONFLICT = {409: {"description": "La operación no es válida en el estado actual"}}


def _framework_out(db: DB, f: CompetencyFramework) -> FrameworkOut:
    competencies = [
        CompetencyOut(id=c.id, codigo=c.codigo, nombre=c.nombre, descripcion=c.descripcion, level_1=c.level_1, level_2=c.level_2, level_3=c.level_3, orden=c.orden)
        for c in competencies_of(db, f.id)
    ]
    return FrameworkOut(id=f.id, program_id=f.program_id, version=f.version, estado=f.estado, created_at=f.created_at, published_at=f.published_at, competencies=competencies)


@router.post("/programs/{program_id}/competency-frameworks", response_model=FrameworkOut, status_code=201, responses={**_ERRORS, **_CONFLICT},
             summary="Crear una versión borrador del árbol de competencias de un bootcamp")
def post_framework(body: FrameworkWrite, p: CurrentPrincipal, db: DB, program_id: str = ProgramId) -> FrameworkOut:
    program = require_program(db, p, "competencies.configure", program_id)
    return _framework_out(db, create_draft(db, p, program, body.competencies))


@router.get("/programs/{program_id}/competency-frameworks", response_model=FrameworkList, responses=_ERRORS,
            summary="Versiones del árbol de competencias de un bootcamp (borrador, publicada y archivadas)")
def list_frameworks(p: CurrentPrincipal, db: DB, program_id: str = ProgramId) -> FrameworkList:
    require_program(db, p, "competencies.read", program_id)
    frameworks = db.scalars(select(CompetencyFramework).where(CompetencyFramework.program_id == program_id).order_by(CompetencyFramework.version))
    return FrameworkList(program_id=program_id, items=[_framework_out(db, f) for f in frameworks])


@router.put("/competency-frameworks/{framework_id}/competencies", response_model=FrameworkOut, responses={**_ERRORS, **_CONFLICT},
            summary="Sustituir las competencias de un borrador (las versiones publicadas no se editan)")
def put_framework_competencies(framework_id: uuid.UUID, body: FrameworkWrite, p: CurrentPrincipal, db: DB) -> FrameworkOut:
    framework = load_framework(db, framework_id, lock=True)
    require_program(db, p, "competencies.configure", framework.program_id)
    return _framework_out(db, update_draft(db, p, framework, body.competencies))


@router.post("/competency-frameworks/{framework_id}/publish", response_model=FrameworkOut, responses={**_ERRORS, **_CONFLICT},
             summary="Publicar un borrador; la versión publicada anterior pasa a archivada y sigue consultable")
def post_publish(framework_id: uuid.UUID, p: CurrentPrincipal, db: DB) -> FrameworkOut:
    framework = load_framework(db, framework_id, lock=True)
    require_program(db, p, "competencies.configure", framework.program_id)
    return _framework_out(db, publish(db, p, framework))


@router.put("/cohorts/{cohort_id}/competency-framework", response_model=CohortCompetencies, responses={**_ERRORS, **_CONFLICT},
            summary="Elegir la versión publicada del árbol que usa una cohorte")
def put_cohort_framework(body: CohortFrameworkWrite, p: CurrentPrincipal, db: DB, cohort_id: str = CohortId) -> CohortCompetencies:
    cohort = require_cohort(db, p, "competencies.configure", cohort_id)
    framework = load_framework(db, body.framework_id)
    assign_to_cohort(db, p, cohort, framework)
    return CohortCompetencies(cohort_id=cohort.id, framework=_framework_out(db, framework))


@router.get("/cohorts/{cohort_id}/competencies", response_model=CohortCompetencies, responses=_ERRORS,
            summary="Competencias que se evalúan en una cohorte (versión del árbol asignada)")
def get_cohort_competencies(p: CurrentPrincipal, db: DB, cohort_id: str = CohortId) -> CohortCompetencies:
    require_cohort(db, p, "competencies.read", cohort_id)
    framework = cohort_framework(db, cohort_id)
    return CohortCompetencies(cohort_id=cohort_id, framework=_framework_out(db, framework) if framework else None)


@router.post("/enrollments/{enrollment_id}/assessments", response_model=AssessmentOut, status_code=201, responses={**_ERRORS, **_CONFLICT},
             summary="Registrar el nivel 1–3 de un coder en una competencia, con evidencia")
def post_assessment(enrollment_id: uuid.UUID, body: AssessmentWrite, p: CurrentPrincipal, db: DB) -> AssessmentOut:
    enrollment, _ = require_enrollment(db, p, "competencies.assess", enrollment_id)
    a = assess(db, p, enrollment, body)
    competency = db.get(Competency, a.competency_id)
    framework = db.get(CompetencyFramework, competency.framework_id)
    return AssessmentOut(id=a.id, enrollment_id=a.enrollment_id, competency_id=a.competency_id, codigo=competency.codigo, framework_version=framework.version,
                         level=a.level, evidence=a.evidence, assessed_by=p.user.display_name, assessed_at=a.assessed_at)


@router.get("/enrollments/{enrollment_id}/assessments", response_model=EnrollmentAssessments, responses=_ERRORS,
            summary="Nivel actual por competencia y todo el historial de evaluaciones de una matrícula")
def list_assessments(enrollment_id: uuid.UUID, p: CurrentPrincipal, db: DB) -> EnrollmentAssessments:
    enrollment, _ = require_enrollment(db, p, "competencies.read", enrollment_id)
    rows = db.execute(
        select(CompetencyAssessment, Competency, CompetencyFramework, User)
        .join(Competency, Competency.id == CompetencyAssessment.competency_id)
        .join(CompetencyFramework, CompetencyFramework.id == Competency.framework_id)
        .join(User, User.id == CompetencyAssessment.assessed_by)
        .where(CompetencyAssessment.enrollment_id == enrollment.id)
        .order_by(CompetencyAssessment.assessed_at, CompetencyAssessment.id)
    ).all()
    history = [
        AssessmentOut(id=a.id, enrollment_id=a.enrollment_id, competency_id=c.id, codigo=c.codigo, framework_version=f.version,
                      level=a.level, evidence=a.evidence, assessed_by=u.display_name, assessed_at=a.assessed_at)
        for a, c, f, u in rows
    ]
    framework = cohort_framework(db, enrollment.cohort_id)
    latest = {h.competency_id: h for h in history}  # history is chronological, so the last one wins
    current = [
        CurrentLevel(competency_id=c.id, codigo=c.codigo, nombre=c.nombre,
                     level=latest[c.id].level if c.id in latest else None, assessed_at=latest[c.id].assessed_at if c.id in latest else None)
        for c in (competencies_of(db, framework.id) if framework else [])
    ]
    return EnrollmentAssessments(enrollment_id=enrollment.id, framework_version=framework.version if framework else None, current=current, history=history)
