"""Join Zoom provisioning and staff assignment history."""
from collections.abc import Sequence

revision: str = "0026_merge_zoom_staff_history"
down_revision: tuple[str, str] = ("0025_zoom_provisioning_intents", "0025_merge_staff_history_head")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
