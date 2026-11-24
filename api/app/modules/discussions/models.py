"""Scoped discussion persistence; deliberately no public or authorization-bypassing endpoints."""
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, ForeignKeyConstraint, Integer, String, UniqueConstraint, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base, utcnow


class DiscussionThread(Base):
    __tablename__ = 'discussion_thread'
    __table_args__ = (
        CheckConstraint("(scope_type = 'application' AND application_id IS NOT NULL AND program_id IS NULL) OR "
                        "(scope_type = 'program' AND program_id IS NOT NULL AND application_id IS NULL)", name='ck_discussion_thread_scope'),
        CheckConstraint('length(trim(subject)) BETWEEN 1 AND 160', name='ck_discussion_thread_subject'),
        CheckConstraint('(resolved_by IS NULL) = (resolved_at IS NULL)', name='ck_discussion_thread_resolution'),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    scope_type: Mapped[str] = mapped_column(String(12))
    application_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('application.id'), index=True)
    program_id: Mapped[str | None] = mapped_column(ForeignKey('program.id'), index=True)
    subject: Mapped[str] = mapped_column(String(160))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey('app_user.id'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey('app_user.id'))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class DiscussionComment(Base):
    __tablename__ = 'discussion_comment'
    __table_args__ = (
        UniqueConstraint('thread_id', 'id', name='uq_discussion_comment_thread_id'),
        ForeignKeyConstraint(['thread_id', 'parent_id'], ['discussion_comment.thread_id', 'discussion_comment.id'],
                             name='fk_discussion_comment_parent_thread'),
        CheckConstraint('parent_id IS NULL OR parent_id <> id', name='ck_discussion_comment_not_self'),
        CheckConstraint('length(trim(body)) BETWEEN 1 AND 2000', name='ck_discussion_comment_body'),
        CheckConstraint('version >= 1', name='ck_discussion_comment_version'),
        CheckConstraint('edited_at IS NULL OR edited_at >= created_at', name='ck_discussion_comment_edited'),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('discussion_thread.id'), index=True)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey('app_user.id'))
    body: Mapped[str] = mapped_column(String(2000))
    version: Mapped[int] = mapped_column(Integer, default=1, server_default=text('1'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
