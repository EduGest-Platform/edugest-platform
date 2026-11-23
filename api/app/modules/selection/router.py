import uuid

from fastapi import APIRouter, status
from sqlalchemy import select

from app.core import audit
from app.core.deps import DB, CurrentPrincipal
from app.core.errors import UserFacingError
from app.modules.admissions.models import Application
from app.modules.catalog.models import Call
from app.modules.identity.models import User
from app.modules.selection.models import SelectionDecision
from app.modules.selection.schemas import SelectionDecisionList, SelectionDecisionOut, SelectionDecisionWrite
from app.modules.selection.service import decide, require_selection_access

router = APIRouter(tags=["selection"])

_ERRORS = {403: {"description": "Sin permiso sobre el ámbito"}, 404: {"description": "No encontrado"}}


def _out(decision: SelectionDecision, actor_name: str | None) -> SelectionDecisionOut:
    return SelectionDecisionOut(
        id=decision.id, application_id=decision.application_id, decision=decision.decision, from_stage=decision.from_stage,
        to_stage=decision.to_stage, reason=decision.reason, actor=actor_name, occurred_at=decision.occurred_at,
        cohort_id=decision.cohort_id, enrollment_id=decision.enrollment_id,
    )


@router.post(
    "/applications/{application_id}/selection-decisions",
    response_model=SelectionDecisionOut,
    status_code=201,
    responses={
        **_ERRORS,
        409: {"description": "La selección ya terminó, no hay plazas o la persona ya está matriculada en esa cohorte"},
        422: {"description": "Datos no válidos o cohorte que no pertenece a la convocatoria"},
    },
    summary="Terminar la selección con una decisión humana: admitir (y matricular), lista de espera o no admitida",
)
def post_selection_decision(application_id: uuid.UUID, body: SelectionDecisionWrite, p: CurrentPrincipal, db: DB) -> SelectionDecisionOut:
    decision = decide(db, p, application_id, body)
    return _out(decision, p.user.display_name)


@router.get(
    "/applications/{application_id}/selection-decisions",
    response_model=SelectionDecisionList,
    responses=_ERRORS,
    summary="Historial de decisiones de admisión de una candidatura",
)
def list_selection_decisions(application_id: uuid.UUID, p: CurrentPrincipal, db: DB) -> SelectionDecisionList:
    row = db.execute(select(Application, Call).join(Call, Call.id == Application.call_id).where(Application.id == application_id)).first()
    if not row:
        raise UserFacingError(status.HTTP_404_NOT_FOUND, "application_not_found", "No encontramos esta candidatura. Vuelve a la lista y ábrela de nuevo.")
    application, call = row
    require_selection_access(db, p, "selection.read", call)
    decisions = list(db.scalars(select(SelectionDecision).where(SelectionDecision.application_id == application.id).order_by(SelectionDecision.occurred_at)))
    ids = {d.actor_user_id for d in decisions}
    names = {u.id: u.display_name for u in db.scalars(select(User).where(User.id.in_(ids)))} if ids else {}
    audit.record(db, p, "selection.decisions_viewed", "application", str(application.id), codigo=application.codigo)
    db.commit()
    return SelectionDecisionList(application_id=application.id, items=[_out(d, names.get(d.actor_user_id)) for d in decisions])
