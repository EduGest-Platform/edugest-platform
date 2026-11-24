"""Preserve authority at vote time; legacy votes remain explicitly unknown."""
from alembic import op
import sqlalchemy as sa

revision = '0014'
down_revision = '0013'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('selection_approval', sa.Column('authority', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('selection_approval', 'authority')
