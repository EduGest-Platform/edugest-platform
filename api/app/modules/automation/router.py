import uuid

from fastapi import APIRouter, Query, Response
from sqlalchemy import func, select

from app.core import audit
from app.core.deps import CurrentPrincipal, DB
from app.modules.automation.models import AutomationExecution, SimulatedReminder
from app.modules.automation.schemas import AutomationExecutionList, AutomationExecutionOut
from app.modules.automation.reminders import simulate_reminder
from app.modules.automation.schemas import (
    ReminderSimulationRequest, ReminderSimulationResult, SimulatedReminderList, SimulatedReminderOut,
)
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


@router.post("/applications/{application_id}/simulated-reminders", response_model=ReminderSimulationResult,
             status_code=201, responses={**ERRORS, 200: {"model": ReminderSimulationResult},
                                        409: {"description": "Fuera de preselección (simulation_outside_preselection)"}},
             summary="Simular recordatorio con fecha introducida por personal, sin enviar ni resolver tareas")
def create_simulated_reminder(application_id: uuid.UUID, body: ReminderSimulationRequest,
                              response: Response, p: CurrentPrincipal, db: DB) -> ReminderSimulationResult:
    reminder, created = simulate_reminder(db, p, application_id, body)
    if not created:
        response.status_code = 200
    return ReminderSimulationResult(outcome="simulated_reminder" if reminder else "not_due",
                                    reminder=SimulatedReminderOut.model_validate(reminder) if reminder else None)


@router.get("/applications/{application_id}/simulated-reminders", response_model=SimulatedReminderList,
            responses=ERRORS, summary="Historial de simulaciones, nunca recibos de entrega")
def list_simulated_reminders(application_id: uuid.UUID, p: CurrentPrincipal, db: DB,
                             limit: int = Query(50, ge=1, le=100)) -> SimulatedReminderList:
    application, call = load_application(db, application_id)
    require_access(db, p, "applications.read", call)
    condition = SimulatedReminder.application_id == application.id
    total = db.scalar(select(func.count()).select_from(SimulatedReminder).where(condition))
    rows = db.scalars(select(SimulatedReminder).where(condition)
                      .order_by(SimulatedReminder.simulated_at.desc(), SimulatedReminder.id).limit(limit)).all()
    audit.record(db, p, "simulated_reminder.list_viewed", "application", str(application.id), returned=len(rows), total=total)
    db.commit()
    return SimulatedReminderList(application_id=application.id,
                                 items=[SimulatedReminderOut.model_validate(row) for row in rows], total=total, limit=limit)
