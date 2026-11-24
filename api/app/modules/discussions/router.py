import uuid
from typing import Literal

from fastapi import APIRouter, Query
from pydantic import ValidationError

from app.core.deps import DB, CurrentPrincipal
from app.core.errors import UserFacingError
from app.modules.discussions import service
from app.modules.discussions.schemas import ThreadCreate, ThreadList, ThreadOut, ThreadScope
from app.modules.discussions.schemas import CommentCreate, CommentList, CommentOut

router = APIRouter(tags=['discussions'])
ERRORS = {403: {'description': 'Sin permiso en el ámbito'}, 404: {'description': 'Hilo o ámbito no encontrado'}}


@router.post('/discussion-threads', response_model=ThreadOut, status_code=201, responses=ERRORS,
             summary='Crear un hilo interno en un expediente o programa autorizado')
def post_thread(body: ThreadCreate, p: CurrentPrincipal, db: DB):
    return service.create_thread(db, p, body)


@router.get('/discussion-threads', response_model=ThreadList, responses=ERRORS,
            summary='Hilos de un único ámbito autorizado, paginados sin datos de otros ámbitos')
def list_threads(p: CurrentPrincipal, db: DB, scope_type: Literal['application', 'program'],
                 application_id: uuid.UUID | None = None, program_id: str | None = Query(default=None, min_length=1, max_length=20),
                 limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0)):
    try:
        scope = ThreadScope(scope_type=scope_type, application_id=application_id, program_id=program_id)
    except ValidationError:
        raise UserFacingError(422, 'invalid_discussion_scope', 'Indica solo el expediente o el programa del ámbito elegido.') from None
    return service.list_threads(db, p, scope, limit, offset)


@router.get('/discussion-threads/{thread_id}', response_model=ThreadOut, responses=ERRORS,
            summary='Consultar un hilo interno, comprobando los permisos del expediente o programa')
def get_thread(thread_id: uuid.UUID, p: CurrentPrincipal, db: DB):
    return service.get_thread(db, p, thread_id)


@router.post('/discussion-threads/{thread_id}/comments', response_model=CommentOut, status_code=201,
             responses={**ERRORS, 409: {'description': 'Hilo resuelto'}}, summary='Añadir comentario o respuesta dentro de un hilo autorizado')
def post_comment(thread_id: uuid.UUID, body: CommentCreate, p: CurrentPrincipal, db: DB):
    return service.create_comment(db, p, thread_id, body)


@router.get('/discussion-threads/{thread_id}/comments', response_model=CommentList, responses=ERRORS,
            summary='Comentarios paginados de un hilo autorizado, con referencias al comentario padre')
def get_comments(thread_id: uuid.UUID, p: CurrentPrincipal, db: DB,
                 limit: int = Query(default=50, ge=1, le=200), offset: int = Query(default=0, ge=0)):
    return service.list_comments(db, p, thread_id, limit, offset)
