"""merge portfolio and selection appointments heads

Revision ID: 0024
Revises: 0023_portfolio, 0023_selection_appointments
Create Date: 2026-11-27 10:00:00.000000

Both 0023 migrations branched from 0022 in parallel PRs (KAN-59 and
KAN-155). They create independent tables, so this merge revision only
joins the two heads and changes no schema.
"""
from collections.abc import Sequence


revision: str = '0024'
down_revision: tuple[str, str] = ('0023_portfolio', '0023_selection_appointments')
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
