import uuid

from fastapi import APIRouter

from app.core.deps import DB, CurrentPrincipal
from app.modules.learning import documentation_service as service
from app.modules.learning.documentation_schemas import DocumentationOut, DocumentationWrite

router = APIRouter(prefix='/enrollments/{enrollment_id}/documentation', tags=['learning'])
ERRORS = {403: {'description': 'Outside authorized scope'}, 404: {'description': 'Enrollment not found'}}


@router.get('', response_model=DocumentationOut, responses=ERRORS,
            summary='Read own or authorized admission-scope documentation status')
def read_documentation(enrollment_id: uuid.UUID, p: CurrentPrincipal, db: DB):
    return service.read_documentation(db, p, enrollment_id)


@router.post('/accredit', response_model=DocumentationOut,
             responses={**ERRORS, 409: {'description': 'Stale version or unverifiable active admission'}},
             summary='Record a human administrative accreditation, without granting academic access')
def accredit_documentation(enrollment_id: uuid.UUID, body: DocumentationWrite, p: CurrentPrincipal, db: DB):
    return service.accredit_documentation(db, p, enrollment_id, body)
