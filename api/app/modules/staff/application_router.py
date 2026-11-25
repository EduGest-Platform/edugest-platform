import uuid

from fastapi import APIRouter

from app.core.deps import DB, CurrentPrincipal
from app.modules.staff import application_service as service
from app.modules.staff.application_schemas import AccessApplicationPreview

router = APIRouter(prefix='/staff/access-requests', tags=['staff'])
ERRORS = {403: {'description': 'Global administration required'}, 404: {'description': 'Request not found'}}


@router.get('/{request_id}/application-preview', response_model=AccessApplicationPreview, responses=ERRORS,
            summary='Preview application blockers without changing access; revalidated on application')
def preview_application(request_id: uuid.UUID, p: CurrentPrincipal, db: DB):
    return service.preview_application(db, p, request_id)
