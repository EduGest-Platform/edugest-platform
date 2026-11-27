"""own learner portfolio link

Revision ID: 0023_portfolio
Revises: 0022
Create Date: 2026-11-26 16:27:43.972413
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0023_portfolio'
down_revision: str | None = '0022'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'portfolio_link',
        sa.Column('enrollment_id', sa.Uuid(), nullable=False),
        sa.Column('url', sa.String(length=160), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['enrollment_id'], ['enrollment.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('enrollment_id'),
    )


def downgrade() -> None:
    op.drop_table('portfolio_link')
