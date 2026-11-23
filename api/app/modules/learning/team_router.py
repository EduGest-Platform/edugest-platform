"""Teaching team of a cohort (Melissa round 3, Q15, approved by the PO 23/11/2026).

A teacher of a cohort can add or remove other teachers of that same cohort. Only the "docente" role on that
cohort can be granted here, so nobody can escalate to admissions, coordination or admin. Every change is audited,
and the last teacher of a cohort cannot be removed (the cohort would be left without anyone to manage it).
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Path, status
from pydantic import BaseModel
from sqlalchemy import select

from app.core import audit
from app.core.authz import TEAM_MANAGE_PERMISSION
from app.core.db import utcnow
from app.core.deps import DB, CurrentPrincipal
from app.core.errors import UserFacingError
from app.modules.identity.models import RoleAssignment, User
from app.modules.learning.access import require_cohort

router = APIRouter(tags=["teaching-team"])

CohortId = Path(max_length=20)
TEACHER_ROLE = "docente"
_ERRORS = {403: {"description": "Sin permiso sobre la cohorte"}, 404: {"description": "No encontrado"}}


class TeamMember(BaseModel):
    user_id: uuid.UUID
    display_name: str
    granted_at: datetime


class TeachingTeam(BaseModel):
    cohort_id: str
    members: list[TeamMember]


def _active_teachers(db: DB, cohort_id: str) -> list[RoleAssignment]:
    query = select(RoleAssignment).where(
        RoleAssignment.role == TEACHER_ROLE, RoleAssignment.scope_type == "cohort", RoleAssignment.scope_id == cohort_id,
        RoleAssignment.revoked_at.is_(None),
    )
    return list(db.scalars(query.order_by(RoleAssignment.created_at)))


def _team(db: DB, cohort_id: str) -> TeachingTeam:
    rows = _active_teachers(db, cohort_id)
    users = {u.id: u for u in db.scalars(select(User).where(User.id.in_({r.user_id for r in rows})))} if rows else {}
    return TeachingTeam(cohort_id=cohort_id, members=[TeamMember(user_id=r.user_id, display_name=users[r.user_id].display_name, granted_at=r.created_at) for r in rows])


def _staff_user(db: DB, user_id: uuid.UUID) -> User:
    """Only staff accounts can teach: a person account (applicant or coder) is never given an internal role."""
    user = db.get(User, user_id)
    if not user or not user.is_active:
        raise UserFacingError(status.HTTP_404_NOT_FOUND, "user_not_found", "No encontramos esta cuenta de personal.")
    if user.person_id is not None:
        raise UserFacingError(status.HTTP_409_CONFLICT, "person_account", "Esta cuenta es de una persona candidata o coder; no puede formar parte del equipo docente.")
    return user


@router.get("/cohorts/{cohort_id}/teaching-team", response_model=TeachingTeam, responses=_ERRORS, summary="Equipo docente de una cohorte")
def get_team(p: CurrentPrincipal, db: DB, cohort_id: str = CohortId) -> TeachingTeam:
    require_cohort(db, p, TEAM_MANAGE_PERMISSION, cohort_id)
    return _team(db, cohort_id)


@router.put("/cohorts/{cohort_id}/teaching-team/{user_id}", response_model=TeachingTeam, responses={**_ERRORS, 409: {"description": "Cuenta de persona, no de personal"}},
            summary="Añadir una persona del personal como docente de la cohorte")
def add_teacher(user_id: uuid.UUID, p: CurrentPrincipal, db: DB, cohort_id: str = CohortId) -> TeachingTeam:
    require_cohort(db, p, TEAM_MANAGE_PERMISSION, cohort_id)
    user = _staff_user(db, user_id)
    row = db.scalar(select(RoleAssignment).where(RoleAssignment.user_id == user.id, RoleAssignment.role == TEACHER_ROLE,
                                                 RoleAssignment.scope_type == "cohort", RoleAssignment.scope_id == cohort_id))
    if row is None:
        db.add(RoleAssignment(user_id=user.id, role=TEACHER_ROLE, scope_type="cohort", scope_id=cohort_id, granted_by=p.user.id))
    elif row.revoked_at is not None:
        row.revoked_at, row.granted_by, row.created_at = None, p.user.id, utcnow()
    audit.record(db, p, "cohort.teacher_added", "cohort", cohort_id, user_id=str(user.id))
    db.commit()
    return _team(db, cohort_id)


@router.delete("/cohorts/{cohort_id}/teaching-team/{user_id}", response_model=TeachingTeam, responses={**_ERRORS, 409: {"description": "Es la última persona docente de la cohorte"}},
               summary="Quitar a una persona del equipo docente de la cohorte")
def remove_teacher(user_id: uuid.UUID, p: CurrentPrincipal, db: DB, cohort_id: str = CohortId) -> TeachingTeam:
    require_cohort(db, p, TEAM_MANAGE_PERMISSION, cohort_id)
    active = _active_teachers(db, cohort_id)
    row = next((r for r in active if r.user_id == user_id), None)
    if row is None:
        raise UserFacingError(status.HTTP_404_NOT_FOUND, "not_in_team", "Esta persona no forma parte del equipo docente de la cohorte.")
    if len(active) == 1:
        raise UserFacingError(status.HTTP_409_CONFLICT, "last_teacher", "Es la única persona docente de la cohorte. Añade a otra antes de quitarla.")
    row.revoked_at = utcnow()
    audit.record(db, p, "cohort.teacher_removed", "cohort", cohort_id, user_id=str(user_id))
    db.commit()
    return _team(db, cohort_id)
