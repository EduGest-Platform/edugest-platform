"""Next action of a CRM contact (KAN-272): who may own it and how it is read back."""

import uuid
from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.authz import Principal, Scope
from app.core.deps import DB
from app.modules.admissions.models import ApplicationEvent
from app.modules.admissions.schemas import NextActionCreate, NextActionOut
from app.modules.catalog.models import Call
from app.modules.identity.models import RoleAssignment, User

OWNER_PERMISSION = "applications.crm"
TEAM_TIMEZONE = ZoneInfo("Europe/Madrid")


def today() -> date:
    return datetime.now(TEAM_TIMEZONE).date()


def eligible_owners(db: DB, call: Call) -> list[User]:
    """Active staff accounts (never applicant or coder accounts) that hold the CRM permission on this call."""
    rows = db.execute(
        select(User, RoleAssignment)
        .join(RoleAssignment, RoleAssignment.user_id == User.id)
        .where(User.is_active, User.person_id.is_(None), RoleAssignment.revoked_at.is_(None))
        .order_by(User.display_name, User.id)
    ).all()
    principals: dict[uuid.UUID, Principal] = {}
    for user, assignment in rows:
        principals.setdefault(user.id, Principal(user=user, assignments=[])).assignments.append(assignment)
    scope = Scope(program_id=call.program_id, call_id=call.id)
    return [p.user for p in principals.values() if p.can(OWNER_PERMISSION, scope)]


def rejection_reason(db: DB, call: Call, requested: NextActionCreate) -> str | None:
    if requested.due_on < today():
        return "El plazo de la próxima acción no puede ser anterior a hoy"
    if requested.owner_user_id not in {user.id for user in eligible_owners(db, call)}:
        return "La persona responsable no tiene permiso CRM en esta convocatoria"
    return None


def owner_names(db: DB, events: list[ApplicationEvent]) -> dict[uuid.UUID, str]:
    ids = {e.next_action_owner_id for e in events if e.next_action_owner_id}
    if not ids:
        return {}
    return dict(db.execute(select(User.id, User.display_name).where(User.id.in_(ids))).all())


def next_action_out(event: ApplicationEvent, names: dict[uuid.UUID, str]) -> NextActionOut | None:
    if event.next_action is None:
        return None
    return NextActionOut(
        description=event.next_action, owner_user_id=event.next_action_owner_id,
        owner=names[event.next_action_owner_id], due_on=event.next_action_due_on,
    )
