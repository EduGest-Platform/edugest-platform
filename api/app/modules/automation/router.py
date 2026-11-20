import uuid

from fastapi import APIRouter, Query, Response
from sqlalchemy import func, select

from app.core import audit
from app.core.deps import CurrentPrincipal, DB
from app.modules.automation.models import AutomationExecution
from app.modules.automation.schemas import AutomationExecutionList, AutomationExecutionOut
from app.modules.automation.service import record_requirement_execution
from app.modules.requirements.schemas import PrefilterRequest
from app.modules.requirements.service import load_application, require_access

router = APIRouter(tags=["automation"])
ERRORS = {403: {"description": "Sin permiso o fuera de ámbito"}, 404: {"description": "Candidatura o requisito desconocido"}}


@router.post("/applications/{application_id}/automation-executions/requirement-prefilter",
             response_model=AutomationExecutionOut, status_code=201,
             responses={**ERRORS, 200: {"model": AutomationExecutionOut, "description": "Mismo snapshot y día UTC: reintento sin duplicado"}},
             summary="Evaluar y registrar el prefiltro, nunca admitir ni entregar recordatorios",
             description="Solo personal con requirements.review. Resultado, clave y día UTC calculados por el servidor. Otro día registra una nueva evaluación. Un registro es evidencia de evaluación, no tarea completada ni ahorro.")
def record_execution(application_id: uuid.UUID, body: PrefilterRequest, response: Response, p: CurrentPrincipal, db: DB) -> AutomationExecutionOut:
    execution, created = record_requirement_execution(db, p, application_id, body)
    if not created:
        response.status_code = 200
    return AutomationExecutionOut.model_validate(execution)


@router.get("/applications/{application_id}/automation-executions", response_model=AutomationExecutionList,
            responses=ERRORS, summary="Historial de evaluaciones del ámbito; total explícito si el límite trunca la lista")
def list_executions(application_id: uuid.UUID, p: CurrentPrincipal, db: DB,
                    limit: int = Query(50, ge=1, le=100)) -> AutomationExecutionList:
    application, call = load_application(db, application_id)
    require_access(db, p, "requirements.read", call)
    condition = AutomationExecution.application_id == application.id
    total = db.scalar(select(func.count()).select_from(AutomationExecution).where(condition))
    executions = db.scalars(select(AutomationExecution).where(condition)
                            .order_by(AutomationExecution.evaluated_at.desc(), AutomationExecution.id).limit(limit)).all()
    audit.record(db, p, "automation_execution.list_viewed", "application", str(application.id), returned=len(executions), total=total)
    db.commit()
    return AutomationExecutionList(application_id=application.id, items=[AutomationExecutionOut.model_validate(e) for e in executions],
                                   total=total, limit=limit)
