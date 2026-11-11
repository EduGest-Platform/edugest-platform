import uuid
from datetime import datetime

from fastapi import APIRouter, Query
from pydantic import BaseModel
from sqlalchemy import select

from app.core.authz import Scope
from app.core.deps import DB, CurrentPrincipal
from app.modules.audit.models import AuditEvent

router = APIRouter(prefix="/audit-events", tags=["audit"])


class AuditEventOut(BaseModel):
    id: int
    at: datetime
    actor_user_id: uuid.UUID | None
    actor_roles: str
    action: str
    target_type: str
    target_id: str | None
    meta: dict


@router.get("", response_model=list[AuditEventOut], summary="Registro de auditoría (solo administración)")
def list_audit(p: CurrentPrincipal, db: DB, target_type: str | None = None, target_id: str | None = None, action: str | None = None, limit: int = Query(100, ge=1, le=500)) -> list[AuditEventOut]:
    p.require("audit.read", Scope())
    q = select(AuditEvent).order_by(AuditEvent.id.desc()).limit(limit)
    if target_type:
        q = q.where(AuditEvent.target_type == target_type)
    if target_id:
        q = q.where(AuditEvent.target_id == target_id)
    if action:
        q = q.where(AuditEvent.action == action)
    return [AuditEventOut.model_validate(e, from_attributes=True) for e in db.scalars(q)]
