"""Persistence foundation; no data backfill or automatic grants."""
from alembic import op
import sqlalchemy as sa

revision = '0015'
down_revision = '0014'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('staff_profile',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('job_title', sa.String(length=120), nullable=True),
        sa.Column('state', sa.String(length=12), nullable=False, server_default='pending'),
        sa.Column('created_by', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("state IN ('pending', 'active', 'inactive')", name='ck_staff_profile_state'),
        sa.UniqueConstraint('user_id', name=None),
        sa.ForeignKeyConstraint(['created_by'], ['app_user.id'], ondelete=None),
        sa.ForeignKeyConstraint(['user_id'], ['app_user.id'], ondelete=None),
    )
    op.create_table('staff_invitation',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('staff_profile_id', sa.Uuid(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('created_by', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('expires_at > created_at', name='ck_staff_invitation_expiry'),
        sa.CheckConstraint("token_hash ~ '^[0-9a-f]{64}$'", name='ck_staff_invitation_hash'),
        sa.CheckConstraint('revoked_at IS NULL OR revoked_at >= created_at', name='ck_staff_invitation_revoked'),
        sa.CheckConstraint('used_at IS NULL OR revoked_at IS NULL', name='ck_staff_invitation_terminal'),
        sa.CheckConstraint('used_at IS NULL OR (used_at >= created_at AND used_at <= expires_at)', name='ck_staff_invitation_used'),
        sa.UniqueConstraint('token_hash', name=None),
        sa.ForeignKeyConstraint(['created_by'], ['app_user.id'], ondelete=None),
        sa.ForeignKeyConstraint(['staff_profile_id'], ['staff_profile.id'], ondelete=None),
    )
    op.create_index('ix_staff_invitation_staff_profile_id', 'staff_invitation', ['staff_profile_id'], unique=False)
    op.create_table('access_change_request',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('staff_profile_id', sa.Uuid(), nullable=False),
        sa.Column('requested_role', sa.String(length=20), nullable=False),
        sa.Column('scope_type', sa.String(length=12), nullable=False),
        sa.Column('scope_id', sa.String(length=30), nullable=True),
        sa.Column('state', sa.String(length=12), nullable=False, server_default='requested'),
        sa.Column('requested_by', sa.Uuid(), nullable=False),
        sa.Column('requested_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reviewed_by', sa.Uuid(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('applied_assignment_id', sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('reviewed_by IS NULL OR reviewed_by <> requested_by', name='ck_access_request_distinct_reviewer'),
        sa.CheckConstraint("(state = 'requested' AND reviewed_by IS NULL AND reviewed_at IS NULL AND applied_assignment_id IS NULL) OR (state IN ('approved', 'rejected') AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL AND applied_assignment_id IS NULL) OR (state IN ('applied', 'revoked') AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL AND applied_assignment_id IS NOT NULL)", name='ck_access_request_review_shape'),
        sa.CheckConstraint("requested_role IN ('admin', 'captacion', 'seleccion', 'docente', 'coordinacion')", name='ck_access_request_role'),
        sa.CheckConstraint("scope_type IN ('global', 'program', 'call', 'cohort')", name='ck_access_request_scope'),
        sa.CheckConstraint("(scope_type = 'global') = (scope_id IS NULL)", name='ck_access_request_scope_id'),
        sa.CheckConstraint("state IN ('requested', 'approved', 'rejected', 'applied', 'revoked')", name='ck_access_request_state'),
        sa.ForeignKeyConstraint(['applied_assignment_id'], ['role_assignment.id'], ondelete=None),
        sa.ForeignKeyConstraint(['requested_by'], ['app_user.id'], ondelete=None),
        sa.ForeignKeyConstraint(['reviewed_by'], ['app_user.id'], ondelete=None),
        sa.ForeignKeyConstraint(['staff_profile_id'], ['staff_profile.id'], ondelete=None),
    )
    op.create_index('ix_access_change_request_staff_profile_id', 'access_change_request', ['staff_profile_id'], unique=False)


def downgrade():
    op.drop_table('access_change_request')
    op.drop_table('staff_invitation')
    op.drop_table('staff_profile')
