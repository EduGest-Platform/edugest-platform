"""Optimistic thread versions and comment tombstones; no automatic access changes."""
from alembic import op
import sqlalchemy as sa

revision = '0017'
down_revision = '0016'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('discussion_thread', sa.Column('version', sa.Integer(), server_default=sa.text('1'), nullable=False))
    op.create_check_constraint('ck_discussion_thread_version', 'discussion_thread', 'version >= 1')
    op.add_column('discussion_comment', sa.Column('deleted_by', sa.Uuid(), nullable=True))
    op.add_column('discussion_comment', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key('fk_discussion_comment_deleted_by', 'discussion_comment', 'app_user', ['deleted_by'], ['id'])
    op.create_check_constraint('ck_discussion_comment_deleted', 'discussion_comment', '(deleted_by IS NULL) = (deleted_at IS NULL)')


def downgrade():
    op.drop_constraint('ck_discussion_comment_deleted', 'discussion_comment', type_='check')
    op.drop_constraint('fk_discussion_comment_deleted_by', 'discussion_comment', type_='foreignkey')
    op.drop_column('discussion_comment', 'deleted_at')
    op.drop_column('discussion_comment', 'deleted_by')
    op.drop_constraint('ck_discussion_thread_version', 'discussion_thread', type_='check')
    op.drop_column('discussion_thread', 'version')
