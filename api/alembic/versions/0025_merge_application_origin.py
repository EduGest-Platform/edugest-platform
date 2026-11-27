"""Merge the application origin head (KAN-275) with the previous merge of migration heads.

No schema change: both parents touch different tables.

Revision ID: 0025_merge_application_origin
Revises: 0023, 0024_merge_heads
"""
from collections.abc import Sequence


revision: str = "0025_merge_application_origin"
down_revision: tuple[str, str] = ("0023", "0024_merge_heads")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
