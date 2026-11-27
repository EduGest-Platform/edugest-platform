"""Preserve revoked scoped assignments when the same access is approved again."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023_role_assignment_history"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index("uq_active_role_assignment", "role_assignment", ["user_id", "role", "scope_type", "scope_id"],
                    unique=True, postgresql_where=sa.text("revoked_at IS NULL"))
    op.drop_constraint("uq_role_assignment", "role_assignment", type_="unique")


def downgrade() -> None:
    # The old constraint cannot represent successive scoped grants. Preserve those rows by refusing the downgrade.
    op.create_unique_constraint("uq_role_assignment", "role_assignment", ["user_id", "role", "scope_type", "scope_id"])
    op.drop_index("uq_active_role_assignment", table_name="role_assignment")
