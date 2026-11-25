"""Record human documentary accreditation without changing academic permissions."""
from alembic import op
import sqlalchemy as sa

revision = '0019'
down_revision = '0018'
branch_labels = None
depends_on = None


def upgrade():
    # Existing rows remain pending: admission alone is not evidence of document verification.
    op.add_column('enrollment', sa.Column('documentation_state', sa.String(12), server_default='pending', nullable=False))
    op.add_column('enrollment', sa.Column('documentation_version', sa.Integer(), server_default=sa.text('1'), nullable=False))
    op.add_column('enrollment', sa.Column('documentation_accredited_by', sa.Uuid(), nullable=True))
    op.add_column('enrollment', sa.Column('documentation_accredited_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key('fk_enrollment_documentation_actor', 'enrollment', 'app_user', ['documentation_accredited_by'], ['id'])
    op.create_check_constraint('ck_enrollment_documentation_state', 'enrollment', "documentation_state IN ('pending','accredited')")
    op.create_check_constraint('ck_enrollment_documentation_version', 'enrollment', 'documentation_version >= 1')
    op.create_check_constraint('ck_enrollment_documentation_evidence', 'enrollment',
        "(documentation_state = 'pending' AND documentation_accredited_by IS NULL AND documentation_accredited_at IS NULL) OR "
        "(documentation_state = 'accredited' AND documentation_accredited_by IS NOT NULL AND documentation_accredited_at IS NOT NULL)")


def downgrade():
    op.drop_constraint('ck_enrollment_documentation_evidence', 'enrollment', type_='check')
    op.drop_constraint('ck_enrollment_documentation_version', 'enrollment', type_='check')
    op.drop_constraint('ck_enrollment_documentation_state', 'enrollment', type_='check')
    op.drop_constraint('fk_enrollment_documentation_actor', 'enrollment', type_='foreignkey')
    for column in ('documentation_accredited_at', 'documentation_accredited_by', 'documentation_version', 'documentation_state'):
        op.drop_column('enrollment', column)
