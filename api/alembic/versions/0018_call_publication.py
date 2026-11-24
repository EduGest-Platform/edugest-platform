"""Separate editorial publication from the admission window."""
from alembic import op
import sqlalchemy as sa

revision = '0018'
down_revision = '0017'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('call', sa.Column('publication_state', sa.String(10), server_default='draft', nullable=False))
    op.add_column('call', sa.Column('publication_version', sa.Integer(), server_default=sa.text('1'), nullable=False))
    # Existing calls were already exposed by the public /calls endpoint. Preserve that visibility;
    # new rows default to draft and require a separate administrative publication action.
    op.execute(sa.text("UPDATE call SET publication_state = 'published'"))
    op.create_check_constraint('ck_call_publication_state', 'call', "publication_state IN ('draft','published')")
    op.create_check_constraint('ck_call_publication_version', 'call', 'publication_version >= 1')


def downgrade():
    op.drop_constraint('ck_call_publication_version', 'call', type_='check')
    op.drop_constraint('ck_call_publication_state', 'call', type_='check')
    op.drop_column('call', 'publication_version')
    op.drop_column('call', 'publication_state')
