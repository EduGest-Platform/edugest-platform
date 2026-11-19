"""KAN-183: immutable, idempotent requirement evaluation records on integrated 0006."""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "automation_execution",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("call_id", sa.String(30), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("rule_version", sa.String(40), nullable=False),
        sa.Column("idempotency_key", sa.String(64), nullable=False),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("stage_at_evaluation", sa.String(40), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("recorded_by", sa.Uuid(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["application_id"], ["application.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["call_id"], ["call.id"]),
        sa.ForeignKeyConstraint(["recorded_by"], ["app_user.id"]),
        sa.UniqueConstraint("idempotency_key", name="uq_automation_execution_key"),
        sa.CheckConstraint("kind = 'requirement_prefilter'", name="ck_automation_execution_kind"),
        sa.CheckConstraint("outcome IN ('human_review', 'no_action')", name="ck_automation_execution_outcome"),
    )
    op.create_index("ix_automation_execution_application_id", "automation_execution", ["application_id"])
    op.create_index("ix_automation_execution_call_id", "automation_execution", ["call_id"])
    op.execute("""CREATE FUNCTION reject_automation_execution_change() RETURNS trigger AS $$
    BEGIN RAISE EXCEPTION 'Automation executions are immutable'; END;
    $$ LANGUAGE plpgsql""")
    op.execute("""CREATE TRIGGER immutable_automation_execution BEFORE UPDATE ON automation_execution
    FOR EACH ROW EXECUTE FUNCTION reject_automation_execution_change()""")


def downgrade():
    op.drop_table("automation_execution")
    op.execute("DROP FUNCTION reject_automation_execution_change()")
