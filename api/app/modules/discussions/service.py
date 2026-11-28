"""Atomic discussion operations with scoped access and metadata-only audit."""
from sqlalchemy import func, select

from app.core import audit
from app.core.db import utcnow
from app.core.errors import UserFacingError
from app.modules.discussions.access import require_any_scope, require_scope, require_thread
from app.modules.discussions.models import DiscussionComment, DiscussionThread
from app.modules.discussions.schemas import CommentMutationOut, CommentOut, ThreadOut, ThreadScope


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


def list_threads(db, actor, scope, limit, offset, resolved=None):
    require_scope(db, actor, scope)
    query = select(DiscussionThread).where(DiscussionThread.scope_type == scope.scope_type)
    if scope.scope_type == 'application':
        query = query.where(DiscussionThread.application_id == scope.application_id)
    else:
        query = query.where(DiscussionThread.program_id == scope.program_id)
    if resolved is not None:
        query = query.where(DiscussionThread.resolved_at.is_not(None) if resolved else DiscussionThread.resolved_at.is_(None))
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
    result = CommentMutationOut(**comment_out(comment).model_dump(), thread_version=thread.version)
    db.commit()
    return result


def list_comments(db, actor, thread_id, limit, offset):
    thread = require_thread(db, actor, thread_id)
    query = select(DiscussionComment).where(DiscussionComment.thread_id == thread.id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = list(db.scalars(query.order_by(DiscussionComment.created_at, DiscussionComment.id).limit(limit).offset(offset)))
    audit.record(db, actor, 'discussion.comments_viewed', 'discussion_thread', str(thread.id))
    db.commit()
    return dict(items=[comment_out(row) for row in rows], total=total)


def require_version(current, expected, kind):
    if current != expected:
        raise UserFacingError(409, f'stale_{kind}', 'Hay una revisión nueva. Actualiza el hilo antes de guardar.')


def require_owner_or_moderator(db, actor, thread, owner_id):
    if owner_id == actor.user.id:
        return
    scope = require_scope(db, actor, ThreadScope(scope_type=thread.scope_type, application_id=thread.application_id, program_id=thread.program_id), write=True)
    # No non-admin role is granted this permission; only an existing matching wildcard can moderate.
    if not actor.can('discussions.moderate', scope):
        raise UserFacingError(403, 'discussion_owner_required', 'Solo la autoría o administración puede realizar este cambio.')


def load_comment_for_change(db, actor, comment_id):
    require_any_scope(actor, write=True)
    thread_id = db.scalar(select(DiscussionComment.thread_id).where(DiscussionComment.id == comment_id))
    if thread_id is None:
        raise UserFacingError(404, 'comment_not_found', 'No encontramos este comentario.')
    # Every write locks thread first, then comment, matching the reply/resolve lock order.
    thread = require_thread(db, actor, thread_id, write=True, lock=True)
    comment = db.scalar(select(DiscussionComment).where(DiscussionComment.id == comment_id, DiscussionComment.thread_id == thread.id).with_for_update())
    if comment is None:
        raise UserFacingError(404, 'comment_not_found', 'No encontramos este comentario.')
    require_owner_or_moderator(db, actor, thread, comment.actor_user_id)
    require_open(thread)
    if comment.deleted_at is not None:
        raise UserFacingError(409, 'comment_deleted', 'Este comentario ya está borrado.')
    return thread, comment


def edit_comment(db, actor, comment_id, body):
    thread, comment = load_comment_for_change(db, actor, comment_id)
    require_version(comment.version, body.expected_version, 'comment')
    comment.body, comment.edited_at = body.body, utcnow()
    comment.version += 1
    thread.version += 1
    audit.record(db, actor, 'discussion.comment_edited', 'discussion_comment', str(comment.id), thread_id=str(thread.id), version=comment.version)
    result = CommentMutationOut(**comment_out(comment).model_dump(), thread_version=thread.version)
    db.commit()
    return result


def delete_comment(db, actor, comment_id, body):
    thread, comment = load_comment_for_change(db, actor, comment_id)
    require_version(comment.version, body.expected_version, 'comment')
    comment.deleted_at, comment.deleted_by = utcnow(), actor.user.id
    comment.version += 1
    thread.version += 1
    audit.record(db, actor, 'discussion.comment_deleted', 'discussion_comment', str(comment.id), thread_id=str(thread.id), version=comment.version)
    result = CommentMutationOut(**comment_out(comment).model_dump(), thread_version=thread.version)
    db.commit()
    return result


def resolve_thread(db, actor, thread_id, body):
    thread = require_thread(db, actor, thread_id, write=True, lock=True)
    require_owner_or_moderator(db, actor, thread, thread.created_by)
    require_version(thread.version, body.expected_version, 'thread')
    if (thread.resolved_at is not None) == body.resolved:
        db.commit()
        return thread_out(thread)
    thread.resolved_by = actor.user.id if body.resolved else None
    thread.resolved_at = utcnow() if body.resolved else None
    thread.version += 1
    audit.record(db, actor, 'discussion.thread_resolved' if body.resolved else 'discussion.thread_reopened',
                 'discussion_thread', str(thread.id), version=thread.version)
    db.commit()
    return thread_out(thread)
