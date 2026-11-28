"""Persist Zoom provisioning intent and join the Zoom and integration histories."""
import sqlalchemy as sa
from alembic import op

revision = "0025_zoom_provisioning_intents"
down_revision = ("0025_merge_application_origin", "0023_zoom_meetings")
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "zoom_provisioning_intent",
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("attendance_session.id"), primary_key=True),
        sa.Column("operation_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("host_id", sa.String(255), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("authentication_mode", sa.String(20), nullable=False),
        sa.Column("profile_id", sa.String(255)),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("updated_by", sa.Uuid(), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("state IN ('pending', 'uncertain', 'confirmed')", name="ck_zoom_intent_state"),
    )


def downgrade() -> None:
    op.drop_table("zoom_provisioning_intent")
