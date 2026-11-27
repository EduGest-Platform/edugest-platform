"""Join staff assignment history with the integration migration head."""
from collections.abc import Sequence

revision: str = "0025_merge_staff_history_head"
down_revision: tuple[str, str] = ("0024_merge_heads", "0023_role_assignment_history")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
