"""Merge portfolio and selection appointment migration heads.

Revision ID: 0024_merge_heads
Revises: 0023_portfolio, 0023_selection_appointments
"""
from collections.abc import Sequence


revision: str = "0024_merge_heads"
down_revision: tuple[str, str] = ("0023_portfolio", "0023_selection_appointments")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
