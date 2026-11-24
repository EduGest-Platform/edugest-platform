from fastapi import APIRouter, Query

from app.core.deps import DB, CurrentPrincipal
from app.modules.catalog import publication_service as service
from app.modules.catalog.publication_schemas import PublicationList, PublicationOut, PublicationState, PublicationUpdate

router = APIRouter(tags=['catalog'])
ERRORS = {403: {'description': 'Global administration required'}, 404: {'description': 'Call not found'}}


@router.get('/catalog/publications', response_model=PublicationList, responses=ERRORS,
            summary='List editorial publication states (global administration)')
def list_publications(p: CurrentPrincipal, db: DB, state: PublicationState | None = None,
                      limit: int = Query(50, ge=1, le=100), offset: int = Query(0, ge=0)):
    return service.list_publications(db, p, state, limit, offset)


@router.get('/calls/{call_id}/publication', response_model=PublicationOut, responses=ERRORS,
            summary='Read editorial publication version (global administration)')
def get_publication(call_id: str, p: CurrentPrincipal, db: DB):
    return service.publication_out(service.get_publication(db, p, call_id))


@router.put('/calls/{call_id}/publication', response_model=PublicationOut,
            responses={**ERRORS, 409: {'description': 'Stale publication version'}},
            summary='Publish or withdraw an offer with optimistic version checking')
def update_publication(call_id: str, body: PublicationUpdate, p: CurrentPrincipal, db: DB):
    return service.update_publication(db, p, call_id, body)
