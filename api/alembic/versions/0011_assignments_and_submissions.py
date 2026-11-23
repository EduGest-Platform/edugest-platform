"""KAN-56: assignments with a deadline and one submission per coder (resubmittable until reviewed)."""
from alembic import op
import sqlalchemy as sa

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "assignment",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("cohort_id", sa.String(20), nullable=False),
        sa.Column("legacy_ref", sa.String(40), nullable=True),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rubric", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["cohort_id"], ["cohort.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["app_user.id"]),
        sa.CheckConstraint("status IN ('draft', 'published')", name="ck_assignment_status"),
    )
    op.create_index("ix_assignment_cohort_id", "assignment", ["cohort_id"])
    op.create_table(
        "submission",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("assignment_id", sa.Uuid(), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("portfolio_url", sa.String(500), nullable=True),
        sa.Column("check_results", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("first_submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by", sa.Uuid(), nullable=False),
        sa.Column("reviewed_by", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["assignment_id"], ["assignment.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["enrollment_id"], ["enrollment.id"]),
        sa.ForeignKeyConstraint(["recorded_by"], ["app_user.id"]),
        sa.ForeignKeyConstraint(["reviewed_by"], ["app_user.id"]),
        sa.UniqueConstraint("assignment_id", "enrollment_id", name="uq_submission_assignment_enrollment"),
        sa.CheckConstraint("status IN ('submitted', 'reviewed')", name="ck_submission_status"),
        sa.CheckConstraint("revision >= 1", name="ck_submission_revision"),
        sa.CheckConstraint("portfolio_url IS NULL OR portfolio_url LIKE 'https://%'", name="ck_submission_portfolio_url"),
        sa.CheckConstraint(
            "(status = 'reviewed' AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)"
            " OR (status = 'submitted' AND reviewed_by IS NULL AND reviewed_at IS NULL)",
            name="ck_submission_review_shape",
        ),
    )
    op.create_index("ix_submission_assignment_id", "submission", ["assignment_id"])
    op.create_index("ix_submission_enrollment_id", "submission", ["enrollment_id"])


def downgrade():
    op.drop_table("submission")
    op.drop_table("assignment")
