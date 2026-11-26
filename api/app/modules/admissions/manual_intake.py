"""KAN-275: manual registration of applications that arrive outside the public form."""

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core import audit
from app.core.authz import APPLICATION_CREATE_PERMISSION, Principal, Scope
from app.modules.admissions.models import Application
from app.modules.admissions.schemas import ManualApplicationCreate
from app.modules.admissions.service import create_application
from app.modules.catalog.models import Call
from app.modules.catalog.publication_policy import require_published

NOT_ALLOWED = "No tienes permiso para registrar candidaturas"
OUT_OF_SCOPE = (
    "No puedes registrar candidaturas en esta convocatoria porque no la tienes asignada. "
    "Si necesitas hacerlo, pide acceso a administración."
)


def _scopes(actor: Principal) -> tuple[bool, set[str], set[str]]:
    """Refuses before any lookup, so a profile without the permission cannot probe which calls exist."""
    is_global, programs, calls = actor.scopes_for(APPLICATION_CREATE_PERMISSION)
    if not (is_global or programs or calls):
        raise HTTPException(status.HTTP_403_FORBIDDEN, NOT_ALLOWED)
    return is_global, programs, calls


def registrable_calls(db: Session, actor: Principal) -> list[Call]:
    """Calls in scope that accept applications today: the same rule as the public form."""
    is_global, programs, calls = _scopes(actor)
    query = select(Call).where(Call.publication_state == "published", Call.estado == "abierta")
    if not is_global:
        query = query.where(or_(Call.program_id.in_(programs), Call.id.in_(calls)))
    return list(db.scalars(query.order_by(Call.nombre)))


def register_application(db: Session, actor: Principal, body: ManualApplicationCreate) -> Application:
    _scopes(actor)
    call = db.get(Call, body.call_id)
    if call is not None and not actor.can(APPLICATION_CREATE_PERMISSION, Scope(program_id=call.program_id, call_id=call.id)):
        audit.record(db, actor, "application.manual_intake_denied", "call", call.id)
        db.commit()
        # An unpublished call stays invisible: outside the scope it answers like an unknown one.
        require_published(call)
        raise HTTPException(status.HTTP_403_FORBIDDEN, OUT_OF_SCOPE)
    # An unknown call gets the same answer as on the public form.
    return create_application(db, body, actor, origin_channel=body.origin_channel)
