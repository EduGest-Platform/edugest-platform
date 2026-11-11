from typing import Literal

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from app.core import audit
from app.core.authz import Scope
from app.core.config import settings
from app.core.deps import DB, CurrentPrincipal
from app.modules.admissions.models import STAGES, Application
from app.modules.catalog.models import Call, Program
from app.modules.catalog.schemas import CallOut, CallSummaryOut, StageCount

router = APIRouter(prefix="/calls", tags=["catalog"])


@router.get("", response_model=list[CallOut], summary="Convocatorias (público: solo datos de la oferta)")
def list_calls(db: DB, estado: Literal["abierta", "cerrada"] | None = None) -> list[CallOut]:
    q = select(Call, Program).join(Program, Program.id == Call.program_id).order_by(Call.opens_on.desc())
    if estado:
        q = q.where(Call.estado == estado)
    return [
        CallOut(id=c.id, program_id=c.program_id, program_nombre=p.nombre, nombre=c.nombre, opens_on=c.opens_on, closes_on=c.closes_on, plazas=c.plazas, estado=c.estado)
        for c, p in db.execute(q)
    ]


@router.get("/{call_id}/summary", response_model=CallSummaryOut, summary="Agregados de una convocatoria, sin datos nominales")
def call_summary(call_id: str, p: CurrentPrincipal, db: DB) -> CallSummaryOut:
    call = db.get(Call, call_id)
    if not call:
        raise HTTPException(404, "Convocatoria no encontrada")
    p.require("calls.aggregate", Scope(program_id=call.program_id, call_id=call.id))
    rows = dict(db.execute(select(Application.stage, func.count()).where(Application.call_id == call_id).group_by(Application.stage)).all())
    total = sum(rows.values())
    small = total < settings.min_group_size
    by_stage = []
    for st in STAGES:
        n = rows.get(st, 0)
        hide = small or (0 < n < settings.min_cell_size)
        by_stage.append(StageCount(stage=st, count=None if hide else n, suppressed=hide))
    audit.record(db, p, "call.summary_viewed", "call", call_id)
    db.commit()
    return CallSummaryOut(call_id=call_id, total=None if small else total, suppressed=small, min_group_size=settings.min_group_size, min_cell_size=settings.min_cell_size, by_stage=by_stage)
