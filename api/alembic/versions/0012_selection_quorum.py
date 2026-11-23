"""Selection quorum per call (default 2, Melissa round 3 Q11) and the approvals that reach it."""
from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("call", sa.Column("selection_quorum", sa.Integer(), nullable=False, server_default=sa.text("2")))
    op.create_check_constraint("ck_call_selection_quorum", "call", "selection_quorum BETWEEN 1 AND 5")
    op.create_table(
        "selection_approval",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("cohort_id", sa.String(20), nullable=True),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decision_id", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["application_id"], ["application.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cohort_id"], ["cohort.id"]),
        sa.ForeignKeyConstraint(["actor_user_id"], ["app_user.id"]),
        sa.ForeignKeyConstraint(["decision_id"], ["selection_decision.id"]),
        sa.CheckConstraint("decision IN ('admitida', 'lista_espera', 'no_admitida')", name="ck_selection_approval_decision"),
        sa.CheckConstraint("length(btrim(reason)) > 0", name="ck_selection_approval_reason"),
        sa.CheckConstraint("(decision = 'admitida') = (cohort_id IS NOT NULL)", name="ck_selection_approval_cohort"),
    )
    op.create_index("ix_selection_approval_application_id", "selection_approval", ["application_id"])
    # One pending vote per person and application: a person cannot reach the quorum alone.
    op.create_index(
        "uq_selection_approval_pending_actor", "selection_approval", ["application_id", "actor_user_id"],
        unique=True, postgresql_where=sa.text("decision_id IS NULL"),
    )


def downgrade():
    op.drop_table("selection_approval")
    op.drop_constraint("ck_call_selection_quorum", "call", type_="check")
    op.drop_column("call", "selection_quorum")
