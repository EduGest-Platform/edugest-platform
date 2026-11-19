"""Preview explicit requirement versions without recording an execution."""
import uuid

from fastapi import APIRouter

from app.core import audit
from app.core.deps import CurrentPrincipal, DB
from app.modules.requirements.prefilter_service import calculate_prefilter
from app.modules.requirements.schemas import PrefilterRequest, PrefilterResult
from app.modules.requirements.service import load_application, require_access

router = APIRouter(tags=["requirements"])


@router.post(
    "/applications/{application_id}/requirement-prefilter",
    response_model=PrefilterResult,
    responses={403: {"description": "Sin permiso o fuera de ámbito"},
               404: {"description": "Candidatura o requisito no encontrado en su convocatoria"},
               422: {"description": "Selección vacía, duplicada o con varias versiones de un código"}},
    summary="Evaluar requisitos seleccionados y proponer revisión humana, nunca decidir admisión",
    description="Selección explícita de versiones, no catálogo activo. Códigos omitidos exigen revisión humana. No escribe tareas ni cambia etapas.",
)
def evaluate_prefilter(application_id: uuid.UUID, body: PrefilterRequest, p: CurrentPrincipal, db: DB) -> PrefilterResult:
    application, call = load_application(db, application_id)
    require_access(db, p, "requirements.read", call)
    result = calculate_prefilter(db, application, call, body)
    audit.record(db, p, "requirement_prefilter.evaluated", "application", str(application.id),
                 definition_ids=[str(item.definition_id) for item in result.items],
                 unresolved_required_count=len(result.unresolved_required_refs), advisory_count=len(result.advisory_refs),
                 unselected_code_count=len(result.unselected_codes))
    db.commit()
    return result
