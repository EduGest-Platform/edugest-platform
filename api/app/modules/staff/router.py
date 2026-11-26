import uuid

from fastapi import APIRouter, Query

from app.core.deps import DB, CurrentPrincipal
from app.modules.staff import service
from app.modules.staff.schemas import InvitationCreate, InvitationIssued, InvitationOut, InvitationRenew
from app.modules.staff.schemas import InvitationAccept, StaffProfileOut
from app.modules.staff.schemas import AccessRequestCreate, AccessRequestList, AccessRequestOut, AccessReview

router = APIRouter(prefix='/staff', tags=['staff'])
ERRORS = {403: {'description': 'Administración global requerida'}, 404: {'description': 'Invitación no encontrada'},
          409: {'description': 'Cuenta/ficha no elegible o invitación ya utilizada'}}


@router.post('/invitations', response_model=InvitationIssued, status_code=201, responses=ERRORS,
             summary='Emitir invitación para una cuenta interna existente, sin conceder roles')
def post_invitation(body: InvitationCreate, p: CurrentPrincipal, db: DB):
    return service.create_invitation(db, p, body)


@router.post('/invitations/{invitation_id}/renew', response_model=InvitationIssued, status_code=201, responses=ERRORS,
             summary='Renovar secreto de invitación y revocar los anteriores no utilizados; sin envío externo')
def renew_invitation(invitation_id: uuid.UUID, body: InvitationRenew, p: CurrentPrincipal, db: DB):
    return service.renew_invitation(db, p, invitation_id, body)


@router.post('/invitations/{invitation_id}/revoke', response_model=InvitationOut, responses=ERRORS,
             summary='Revocar invitación pendiente, sin cambiar roles o sesiones existentes')
def revoke_invitation(invitation_id: uuid.UUID, p: CurrentPrincipal, db: DB):
    return service.revoke_invitation(db, p, invitation_id)


@router.post('/invitations/accept', response_model=StaffProfileOut, responses={400: {'description': 'Invitación no disponible'}, 409: {'description': 'Cuenta no elegible'}},
             summary='Consumir una invitación para la propia cuenta interna, sin conceder roles')
def accept_invitation(body: InvitationAccept, p: CurrentPrincipal, db: DB):
    return service.accept_invitation(db, p, body)


@router.get('/me', response_model=StaffProfileOut, responses={404: {'description': 'Ficha no encontrada'}, 409: {'description': 'Cuenta no elegible'}},
            summary='Consultar únicamente la ficha interna de la sesión actual')
def own_profile(p: CurrentPrincipal, db: DB):
    return service.own_profile(db, p)


@router.post('/access-requests', response_model=AccessRequestOut, status_code=201, responses=ERRORS,
             summary='Solicitar un cambio para la ficha propia; no aplica permisos')
def create_access_request(body: AccessRequestCreate, p: CurrentPrincipal, db: DB):
    return service.create_access_request(db, p, body)


@router.get('/access-requests', response_model=AccessRequestList, responses=ERRORS,
            summary='Solicitudes propias; administración global puede consultar todas')
def list_access_requests(p: CurrentPrincipal, db: DB, limit: int = Query(default=50, ge=1, le=100),
                         offset: int = Query(default=0, ge=0), pending_only: bool = False):
    return service.list_access_requests(db, p, limit, offset, pending_only)


@router.post('/access-requests/{request_id}/review', response_model=AccessRequestOut,
             responses={**ERRORS, 422: {'description': 'Ámbito desconocido'}},
             summary='Revisión administrativa distinta de quien solicita; aprobar no aplica roles')
def review_access_request(request_id: uuid.UUID, body: AccessReview, p: CurrentPrincipal, db: DB):
    return service.review_access_request(db, p, request_id, body)
