"""Atomic discussion operations with scoped access and metadata-only audit."""
from sqlalchemy import func, select

from app.core import audit
from app.modules.discussions.access import require_scope, require_thread
from app.modules.discussions.models import DiscussionThread
from app.modules.discussions.schemas import ThreadOut


def thread_out(thread):
    return ThreadOut.model_validate(thread, from_attributes=True)


def create_thread(db, actor, body):
    require_scope(db, actor, body, write=True)
    thread = DiscussionThread(scope_type=body.scope_type, application_id=body.application_id, program_id=body.program_id,
                              subject=body.subject, created_by=actor.user.id)
    db.add(thread)
    db.flush()
    audit.record(db, actor, 'discussion.thread_created', 'discussion_thread', str(thread.id), scope_type=thread.scope_type)
    db.commit()
    return thread_out(thread)


def list_threads(db, actor, scope, limit, offset):
    require_scope(db, actor, scope)
    query = select(DiscussionThread).where(DiscussionThread.scope_type == scope.scope_type)
    if scope.scope_type == 'application':
        query = query.where(DiscussionThread.application_id == scope.application_id)
    else:
        query = query.where(DiscussionThread.program_id == scope.program_id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = list(db.scalars(query.order_by(DiscussionThread.created_at, DiscussionThread.id).limit(limit).offset(offset)))
    audit.record(db, actor, 'discussion.threads_viewed', 'discussion_scope', str(scope.application_id or scope.program_id), scope_type=scope.scope_type)
    db.commit()
    return dict(items=[thread_out(row) for row in rows], total=total)


def get_thread(db, actor, thread_id):
    thread = require_thread(db, actor, thread_id)
    audit.record(db, actor, 'discussion.thread_viewed', 'discussion_thread', str(thread.id))
    db.commit()
    return thread_out(thread)
