"""Synthetic risk evidence and human interventions; no scoring job or automatic actions."""
from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "risk_alert",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), nullable=False),
        sa.Column("model_version", sa.String(80), nullable=False),
        sa.Column("model_hash", sa.String(64), nullable=False),
        sa.Column("cutoff", sa.Date(), nullable=False),
        sa.Column("status", sa.String(12), nullable=False),
        sa.Column("synthetic_proxy_score", sa.Numeric(8, 7), nullable=True),
        sa.Column("experimental_support_signal", sa.Boolean(), nullable=True),
        sa.Column("abstention_reason", sa.String(120), nullable=True),
        sa.Column("unjustified_absence_days", sa.Numeric(10, 2), nullable=True),
        sa.Column("justified_absence_days", sa.Numeric(10, 2), nullable=True),
        sa.Column("attendance_unknown_fraction", sa.Numeric(8, 7), nullable=True),
        sa.Column("mean_competency_level", sa.Numeric(4, 2), nullable=True),
        sa.Column("synthetic_only", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("human_review_only", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("validated_for_people", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("review_state", sa.String(12), server_default="pending", nullable=False),
        sa.Column("assigned_to", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["enrollment_id"], ["enrollment.id"]),
        sa.ForeignKeyConstraint(["assigned_to"], ["app_user.id"]),
        sa.UniqueConstraint("enrollment_id", "model_hash", "cutoff", name="uq_risk_alert_observation"),
        sa.CheckConstraint("length(model_hash) = 64 AND length(trim(model_version)) > 0", name="ck_risk_alert_provenance"),
        sa.CheckConstraint("synthetic_only AND human_review_only AND NOT validated_for_people", name="ck_risk_alert_synthetic"),
        sa.CheckConstraint("review_state IN ('pending', 'in_review', 'closed')", name="ck_risk_alert_review_state"),
        sa.CheckConstraint("(status = 'scored' AND synthetic_proxy_score BETWEEN 0 AND 1 AND synthetic_proxy_score IS NOT NULL"
                           " AND experimental_support_signal IS NOT NULL AND abstention_reason IS NULL) OR"
                           " (status = 'abstained' AND synthetic_proxy_score IS NULL AND experimental_support_signal IS NULL"
                           " AND abstention_reason IS NOT NULL AND length(trim(abstention_reason)) > 0)", name="ck_risk_alert_score_shape"),
        sa.CheckConstraint("unjustified_absence_days IS NULL OR unjustified_absence_days >= 0", name="ck_risk_alert_unjustified"),
        sa.CheckConstraint("justified_absence_days IS NULL OR justified_absence_days >= 0", name="ck_risk_alert_justified"),
        sa.CheckConstraint("attendance_unknown_fraction IS NULL OR attendance_unknown_fraction BETWEEN 0 AND 1", name="ck_risk_alert_unknown"),
        sa.CheckConstraint("mean_competency_level IS NULL OR mean_competency_level BETWEEN 1 AND 3", name="ck_risk_alert_competency"),
    )
    op.create_index("ix_risk_alert_enrollment_id", "risk_alert", ["enrollment_id"])
    op.create_index("ix_risk_alert_assigned_to", "risk_alert", ["assigned_to"])
    op.create_table(
        "intervention",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("alert_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(12), nullable=False),
        sa.Column("note", sa.String(500), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["alert_id"], ["risk_alert.id"]),
        sa.ForeignKeyConstraint(["actor_user_id"], ["app_user.id"]),
        sa.CheckConstraint("kind IN ('contact', 'support', 'closure')", name="ck_intervention_kind"),
        sa.CheckConstraint("length(trim(note)) BETWEEN 1 AND 500", name="ck_intervention_note"),
    )
    op.create_index("ix_intervention_alert_id", "intervention", ["alert_id"])
    op.create_index("ix_intervention_actor_user_id", "intervention", ["actor_user_id"])


def downgrade():
    op.drop_table("intervention")
    op.drop_table("risk_alert")
