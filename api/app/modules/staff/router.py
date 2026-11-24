import uuid

from fastapi import APIRouter

from app.core.deps import DB, CurrentPrincipal
from app.modules.staff import service
from app.modules.staff.schemas import InvitationCreate, InvitationIssued, InvitationOut, InvitationRenew

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
