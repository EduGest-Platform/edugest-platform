"""Atomic discussion operations with scoped access and metadata-only audit."""
from sqlalchemy import func, select

from app.core import audit
from app.core.errors import UserFacingError
from app.modules.discussions.access import require_scope, require_thread
from app.modules.discussions.models import DiscussionComment, DiscussionThread
from app.modules.discussions.schemas import CommentOut, ThreadOut


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


def comment_out(comment):
    return CommentOut(id=comment.id, thread_id=comment.thread_id, parent_id=comment.parent_id,
                      actor_user_id=comment.actor_user_id, body=None if comment.deleted_at is not None else comment.body,
                      version=comment.version, created_at=comment.created_at, edited_at=comment.edited_at, deleted_at=comment.deleted_at)


def require_open(thread):
    if thread.resolved_at is not None:
        raise UserFacingError(409, 'thread_resolved', 'El hilo está resuelto. Debe reabrirse antes de añadir o editar comentarios.')


def create_comment(db, actor, thread_id, body):
    thread = require_thread(db, actor, thread_id, write=True, lock=True)
    require_open(thread)
    if body.parent_id is not None:
        parent = db.get(DiscussionComment, body.parent_id)
        if parent is None or parent.thread_id != thread.id or parent.deleted_at is not None:
            raise UserFacingError(404, 'parent_not_found', 'No encontramos un comentario padre disponible en este hilo.')
    comment = DiscussionComment(thread_id=thread.id, parent_id=body.parent_id, actor_user_id=actor.user.id, body=body.body)
    db.add(comment)
    db.flush()
    thread.version += 1
    audit.record(db, actor, 'discussion.comment_created', 'discussion_comment', str(comment.id),
                 thread_id=str(thread.id), parent_id=str(comment.parent_id) if comment.parent_id else None, version=comment.version)
    db.commit()
    return comment_out(comment)


def list_comments(db, actor, thread_id, limit, offset):
    thread = require_thread(db, actor, thread_id)
    query = select(DiscussionComment).where(DiscussionComment.thread_id == thread.id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = list(db.scalars(query.order_by(DiscussionComment.created_at, DiscussionComment.id).limit(limit).offset(offset)))
    audit.record(db, actor, 'discussion.comments_viewed', 'discussion_thread', str(thread.id))
    db.commit()
    return dict(items=[comment_out(row) for row in rows], total=total)
