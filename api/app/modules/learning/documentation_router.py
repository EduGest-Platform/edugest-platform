import uuid

from fastapi import APIRouter

from app.core.deps import DB, CurrentPrincipal
from app.modules.learning import documentation_service as service
from app.modules.learning.documentation_schemas import DocumentationOut

router = APIRouter(prefix='/enrollments/{enrollment_id}/documentation', tags=['learning'])
ERRORS = {403: {'description': 'Outside authorized scope'}, 404: {'description': 'Enrollment not found'}}


@router.get('', response_model=DocumentationOut, responses=ERRORS,
            summary='Read own or authorized admission-scope documentation status')
def read_documentation(enrollment_id: uuid.UUID, p: CurrentPrincipal, db: DB):
    return service.read_documentation(db, p, enrollment_id)
