"""KAN-129: isolated simulated reminder evidence after integrated 0008 (attendance and competencies)."""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "simulated_reminder",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("call_id", sa.String(30), nullable=False),
        sa.Column("task_ref", sa.String(80), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rule_version", sa.String(40), nullable=False),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("recorded_by", sa.Uuid(), nullable=False),
        sa.Column("simulated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["application_id"], ["application.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["call_id"], ["call.id"]),
        sa.ForeignKeyConstraint(["recorded_by"], ["app_user.id"]),
        sa.UniqueConstraint("idempotency_key", name="uq_simulated_reminder_key"),
        sa.CheckConstraint("kind IN ('documentation', 'exercises')", name="ck_simulated_reminder_kind"),
    )
    op.create_index("ix_simulated_reminder_application_id", "simulated_reminder", ["application_id"])


def downgrade():
    op.drop_table("simulated_reminder")
