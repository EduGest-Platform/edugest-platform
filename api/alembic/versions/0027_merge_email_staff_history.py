"""Join the email outbox and staff assignment history."""
from collections.abc import Sequence

revision: str = "0027_merge_email_staff_history"
down_revision: tuple[str, str] = ("0026_email_outbox", "0025_merge_staff_history_head")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
