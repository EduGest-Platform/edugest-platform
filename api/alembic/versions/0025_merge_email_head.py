"""Merge the email outbox migration with the current integration head.

Revision ID: 0025_merge_email_head
Revises: 0024_merge_heads, 0023
"""
from collections.abc import Sequence


revision: str = "0025_merge_email_head"
down_revision: tuple[str, str] = ("0024_merge_heads", "0023")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
