"""Conservative discussion access reuses existing application read/CRM authority."""
from sqlalchemy import select

from app.core.authz import Principal, Scope
from app.core.errors import UserFacingError
from app.modules.admissions.models import Application
from app.modules.catalog.models import Call, Program
from app.modules.discussions.models import DiscussionThread
from app.modules.discussions.schemas import ThreadScope


def require_any_scope(actor: Principal, write: bool) -> str:
    permission = 'applications.crm' if write else 'applications.read'
    global_access, programs, calls = actor.scopes_for(permission)
    if not (global_access or programs or calls):
        raise UserFacingError(403, 'discussion_forbidden', 'No tienes permiso para usar estos comentarios internos.')
    return permission


def require_scope(db, actor: Principal, scope: ThreadScope, write=False):
    permission = require_any_scope(actor, write)
    if scope.scope_type == 'application':
        application = db.get(Application, scope.application_id)
        if application is None:
            raise UserFacingError(404, 'application_not_found', 'No encontramos este expediente.')
        call = db.get(Call, application.call_id)
        if call is None:
            raise UserFacingError(404, 'call_not_found', 'No encontramos esta convocatoria.')
        actor.require(permission, Scope(program_id=call.program_id, call_id=call.id))
    else:
        # A call assignment never grants access to every thread of its program.
        actor.require(permission, Scope(program_id=scope.program_id))
        if db.get(Program, scope.program_id) is None:
            raise UserFacingError(404, 'program_not_found', 'No encontramos este programa.')


def require_thread(db, actor: Principal, thread_id, write=False, lock=False):
    require_any_scope(actor, write)
    statement = select(DiscussionThread).where(DiscussionThread.id == thread_id)
    if lock:
        statement = statement.with_for_update()
    thread = db.scalar(statement)
    if thread is None:
        raise UserFacingError(404, 'thread_not_found', 'No encontramos este hilo.')
    require_scope(db, actor, ThreadScope(scope_type=thread.scope_type, application_id=thread.application_id, program_id=thread.program_id), write)
    return thread
