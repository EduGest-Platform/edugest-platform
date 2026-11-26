"""KAN-274: separate person records per intake, with a recorded human review of matching emails.

Existing records keep their links: they were created while the email was unique, so none of them can be a duplicate.

Revision ID: 0021
Revises: 0020
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_person_email", table_name="person")
    op.create_index("ix_person_email", "person", ["email"], unique=False)
    op.create_table(
        "identity_review",
        sa.Column("application_id", sa.Uuid(), nullable=False),
        sa.Column("original_person_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_person_ids", postgresql.ARRAY(sa.Uuid()), nullable=False),
        sa.Column("decision", sa.String(20), nullable=True),
        sa.Column("linked_person_id", sa.Uuid(), nullable=True),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("decided_by", sa.Uuid(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("decision IS NULL OR decision IN ('misma_persona', 'persona_distinta')", name="ck_identity_review_decision"),
        sa.CheckConstraint("num_nonnulls(decision, reason, decided_by, decided_at) IN (0, 4)", name="ck_identity_review_complete"),
        sa.CheckConstraint("(linked_person_id IS NOT NULL) = (decision IS NOT DISTINCT FROM 'misma_persona')", name="ck_identity_review_link"),
        sa.CheckConstraint("reason IS NULL OR length(btrim(reason)) > 0", name="ck_identity_review_reason"),
        sa.CheckConstraint("cardinality(candidate_person_ids) > 0", name="ck_identity_review_candidates"),
        sa.ForeignKeyConstraint(["application_id"], ["application.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["original_person_id"], ["person.id"]),
        sa.ForeignKeyConstraint(["linked_person_id"], ["person.id"]),
        sa.ForeignKeyConstraint(["decided_by"], ["app_user.id"]),
        sa.PrimaryKeyConstraint("application_id"),
    )


def downgrade() -> None:
    """Refuses to run while two records share an email: restoring uniqueness would need someone to merge them."""
    shared = op.get_bind().scalar(sa.text("SELECT count(*) FROM (SELECT email FROM person GROUP BY email HAVING count(*) > 1) AS shared"))
    if shared:
        raise RuntimeError(f"Cannot downgrade 0021: {shared} email(s) belong to more than one person record.")
    op.drop_table("identity_review")
    op.drop_index("ix_person_email", table_name="person")
    op.create_index("ix_person_email", "person", ["email"], unique=True)
