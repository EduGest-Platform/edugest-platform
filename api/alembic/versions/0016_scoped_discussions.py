"""Persistence foundation; no data backfill or automatic grants."""
from alembic import op
import sqlalchemy as sa

revision = '0016'
down_revision = '0015'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('discussion_thread',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('scope_type', sa.String(length=12), nullable=False),
        sa.Column('application_id', sa.Uuid(), nullable=True),
        sa.Column('program_id', sa.String(length=20), nullable=True),
        sa.Column('subject', sa.String(length=160), nullable=False),
        sa.Column('created_by', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_by', sa.Uuid(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('(resolved_by IS NULL) = (resolved_at IS NULL)', name='ck_discussion_thread_resolution'),
        sa.CheckConstraint("(scope_type = 'application' AND application_id IS NOT NULL AND program_id IS NULL) OR (scope_type = 'program' AND program_id IS NOT NULL AND application_id IS NULL)", name='ck_discussion_thread_scope'),
        sa.CheckConstraint('length(trim(subject)) BETWEEN 1 AND 160', name='ck_discussion_thread_subject'),
        sa.ForeignKeyConstraint(['application_id'], ['application.id'], ondelete=None),
        sa.ForeignKeyConstraint(['created_by'], ['app_user.id'], ondelete=None),
        sa.ForeignKeyConstraint(['program_id'], ['program.id'], ondelete=None),
        sa.ForeignKeyConstraint(['resolved_by'], ['app_user.id'], ondelete=None),
    )
    op.create_index('ix_discussion_thread_application_id', 'discussion_thread', ['application_id'], unique=False)
    op.create_index('ix_discussion_thread_program_id', 'discussion_thread', ['program_id'], unique=False)
    op.create_table('discussion_comment',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('thread_id', sa.Uuid(), nullable=False),
        sa.Column('parent_id', sa.Uuid(), nullable=True),
        sa.Column('actor_user_id', sa.Uuid(), nullable=False),
        sa.Column('body', sa.String(length=2000), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('edited_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('length(trim(body)) BETWEEN 1 AND 2000', name='ck_discussion_comment_body'),
        sa.CheckConstraint('edited_at IS NULL OR edited_at >= created_at', name='ck_discussion_comment_edited'),
        sa.CheckConstraint('parent_id IS NULL OR parent_id <> id', name='ck_discussion_comment_not_self'),
        sa.CheckConstraint('version >= 1', name='ck_discussion_comment_version'),
        sa.UniqueConstraint('thread_id', 'id', name='uq_discussion_comment_thread_id'),
        sa.ForeignKeyConstraint(['actor_user_id'], ['app_user.id'], ondelete=None),
        sa.ForeignKeyConstraint(['thread_id'], ['discussion_thread.id'], ondelete=None),
        sa.ForeignKeyConstraint(['thread_id', 'parent_id'], ['discussion_comment.thread_id', 'discussion_comment.id'], ondelete=None),
    )
    op.create_index('ix_discussion_comment_thread_id', 'discussion_comment', ['thread_id'], unique=False)


def downgrade():
    op.drop_table('discussion_comment')
    op.drop_table('discussion_thread')
