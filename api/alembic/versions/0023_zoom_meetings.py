"""KAN-276: Zoom meetings and versioned notes."""
import sqlalchemy as sa
from alembic import op

revision = "0023_zoom_meetings"
down_revision = "0022"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "zoom_meeting",
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("attendance_session.id"), primary_key=True),
        sa.Column("provider_id", sa.String(32), nullable=False, unique=True),
        sa.Column("join_url", sa.String(2048), nullable=False),
        sa.Column("host_id", sa.String(255), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.Column("authentication_mode", sa.String(20), nullable=False),
        sa.Column("profile_id", sa.String(255)),
        sa.Column("ai_settings", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("authentication_mode IN ('open', 'authenticated', 'institutional')", name="ck_zoom_auth_mode"),
        sa.CheckConstraint("(authentication_mode = 'institutional' AND profile_id IS NOT NULL) OR (authentication_mode <> 'institutional' AND profile_id IS NULL)", name="ck_zoom_auth_profile"),
        sa.CheckConstraint("duration_minutes BETWEEN 1 AND 1440", name="ck_zoom_duration"),
    )
    op.create_table(
        "zoom_notes_version",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("zoom_meeting.session_id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("body", sa.JSON(), nullable=False),
        sa.Column("transcript_sha256", sa.String(64), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approved_by", sa.Uuid(), sa.ForeignKey("app_user.id")),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("session_id", "version", name="uq_zoom_notes_version"),
        sa.CheckConstraint("version >= 1", name="ck_zoom_notes_version"),
        sa.CheckConstraint("(approved_by IS NULL AND approved_at IS NULL) OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)", name="ck_zoom_notes_approval"),
    )
    op.create_index("ix_zoom_notes_version_session_id", "zoom_notes_version", ["session_id"])


def downgrade():
    op.drop_index("ix_zoom_notes_version_session_id", table_name="zoom_notes_version")
    op.drop_table("zoom_notes_version")
    op.drop_table("zoom_meeting")
