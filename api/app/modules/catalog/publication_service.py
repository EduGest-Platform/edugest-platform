from sqlalchemy import func, select

from app.core import audit
from app.core.errors import UserFacingError
from app.modules.catalog.models import Call
from app.modules.catalog.publication_policy import check_publication_version, require_publication_admin, require_publishable
from app.modules.catalog.publication_schemas import PublicationOut


def publication_out(call):
    return PublicationOut(call_id=call.id, state=call.publication_state, version=call.publication_version)


def get_publication(db, actor, call_id, lock=False):
    require_publication_admin(actor)
    query = select(Call).where(Call.id == call_id)
    if lock:
        query = query.with_for_update()
    call = db.scalar(query)
    if call is None:
        raise UserFacingError(404, 'call_not_found', 'No encontramos esta convocatoria. Actualiza el listado.')
    return call


def list_publications(db, actor, state, limit, offset):
    require_publication_admin(actor)
    query = select(Call)
    if state is not None:
        query = query.where(Call.publication_state == state)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(Call.id).limit(limit).offset(offset))
    return dict(items=[publication_out(call) for call in rows], total=total)


def update_publication(db, actor, call_id, body):
    call = get_publication(db, actor, call_id, lock=True)
    check_publication_version(call, body.expected_version)
    if body.state == 'published':
        require_publishable(call)
    if call.publication_state != body.state:
        previous = call.publication_state
        call.publication_state = body.state
        call.publication_version += 1
        audit.record(db, actor, 'catalog.publication_changed', 'call', call.id,
                     previous_state=previous, state=call.publication_state, version=call.publication_version)
    db.commit()
    return publication_out(call)
