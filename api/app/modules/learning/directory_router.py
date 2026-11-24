"""Discover cohorts through existing academic permissions; never expose a learner roster."""

from datetime import date

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from app.core.deps import DB, CurrentPrincipal
from app.modules.catalog.models import Cohort
from app.modules.learning.access import cohort_scope

router = APIRouter(tags=["learning"])


class AcademicCohortOut(BaseModel):
    id: str
    program_id: str
    nombre: str
    inicio: date
    fin: date
    timezone: str
    can_record_attendance: bool


@router.get("/cohorts", response_model=list[AcademicCohortOut], summary="Cohortes del ámbito académico autorizado, sin alumnado")
def list_academic_cohorts(p: CurrentPrincipal, db: DB) -> list[AcademicCohortOut]:
    rows = db.scalars(select(Cohort).order_by(Cohort.inicio, Cohort.id))
    return [
        AcademicCohortOut(id=c.id, program_id=c.program_id, nombre=c.nombre, inicio=c.inicio, fin=c.fin, timezone=c.timezone,
                          can_record_attendance=p.can("attendance.record", cohort_scope(c)))
        for c in rows
        if p.can("attendance.read", cohort_scope(c)) or p.can("attendance.aggregate", cohort_scope(c))
    ]
