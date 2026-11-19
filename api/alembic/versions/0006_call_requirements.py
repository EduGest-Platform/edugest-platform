"""KAN-135: immutable per-call requirement definitions.

0005 belongs to the pending preselection-closure PR. Based on current dev (0004);
the second PR to integrate must reconcile the migration chain without rewriting applied migrations.
"""
import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "call_requirement",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("call_id", sa.String(30), nullable=False),
        sa.Column("ref", sa.String(60), nullable=False),
        sa.Column("code", sa.String(60), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(200), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("funder", sa.String(120), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["call_id"], ["call.id"]),
        sa.ForeignKeyConstraint(["created_by"], ["app_user.id"]),
        sa.UniqueConstraint("call_id", "ref", name="uq_call_requirement_ref"),
        sa.UniqueConstraint("call_id", "code", "version", name="uq_call_requirement_code_version"),
        sa.CheckConstraint("kind IN ('required', 'recommended')", name="ck_call_requirement_kind"),
        sa.CheckConstraint("version >= 1", name="ck_call_requirement_version"),
    )
    op.create_index("ix_call_requirement_call_id", "call_requirement", ["call_id"])
    op.add_column("requirement_review", sa.Column("requirement_definition_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_review_definition", "requirement_review", "call_requirement", ["requirement_definition_id"], ["id"])
    op.add_column("requirement_review_revision", sa.Column("requirement_definition_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_review_revision_definition", "requirement_review_revision", "call_requirement", ["requirement_definition_id"], ["id"])
    op.execute("""CREATE FUNCTION reject_requirement_definition_change() RETURNS trigger AS $$
    BEGIN RAISE EXCEPTION 'Requirement definitions are immutable'; END;
    $$ LANGUAGE plpgsql""")
    op.execute("""CREATE TRIGGER immutable_requirement_definition BEFORE UPDATE OR DELETE ON call_requirement
    FOR EACH ROW EXECUTE FUNCTION reject_requirement_definition_change()""")


def downgrade():
    op.drop_constraint("fk_review_revision_definition", "requirement_review_revision", type_="foreignkey")
    op.drop_column("requirement_review_revision", "requirement_definition_id")
    op.drop_constraint("fk_review_definition", "requirement_review", type_="foreignkey")
    op.drop_column("requirement_review", "requirement_definition_id")
    op.drop_table("call_requirement")
    op.execute("DROP FUNCTION reject_requirement_definition_change()")
