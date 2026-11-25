import uuid

from fastapi import APIRouter

from app.core.deps import DB, CurrentPrincipal
from app.modules.staff import application_service as service
from app.modules.staff.application_schemas import AccessApplicationOut, AccessApplicationPreview, AccessApply

router = APIRouter(prefix='/staff/access-requests', tags=['staff'])
ERRORS = {403: {'description': 'Global administration required'}, 404: {'description': 'Request not found'}}


@router.get('/{request_id}/application-preview', response_model=AccessApplicationPreview, responses=ERRORS,
            summary='Preview application blockers without changing access; revalidated on application')
def preview_application(request_id: uuid.UUID, p: CurrentPrincipal, db: DB):
    return service.preview_application(db, p, request_id)


@router.post('/{request_id}/apply', response_model=AccessApplicationOut,
             responses={**ERRORS, 409: {'description': 'Confirmation mismatch or application blocked'}},
             summary='Explicit global-admin application of an approved role request; idempotent for this request')
def apply_access(request_id: uuid.UUID, body: AccessApply, p: CurrentPrincipal, db: DB):
    return service.apply_access(db, p, request_id, body)


@router.get('/{request_id}/application', response_model=AccessApplicationOut,
            responses={**ERRORS, 409: {'description': 'Active internal staff profile required for own-request reads'}},
            summary='Own or global-administrative request application status; no effective-permission claim')
def read_application(request_id: uuid.UUID, p: CurrentPrincipal, db: DB):
    return service.read_application(db, p, request_id)
