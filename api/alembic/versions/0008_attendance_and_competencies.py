"""KAN-55 attendance (sessions, records, correction history, cohort time zone) and KAN-57 versioned competency trees and assessments."""
import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0005"  # current head: 0005 was re-parented onto 0007
branch_labels = None
depends_on = None

RECORD_SHAPE = (
    "(status IN ('presente', 'retraso') AND modality IS NOT NULL AND justification IS NULL)"
    " OR (status = 'ausente' AND modality IS NULL AND justification IS NOT NULL)"
)


# PO 19/11/2026: cohorts run in Spain (peninsula or Canary Islands) or Portugal; "today" follows the cohort's clock.
COHORT_TIMEZONES = "('Europe/Madrid', 'Atlantic/Canary', 'Europe/Lisbon')"


def _cohort_timezone():
    op.add_column("cohort", sa.Column("timezone", sa.String(40), nullable=False, server_default="Europe/Madrid"))
    op.create_check_constraint("ck_cohort_timezone", "cohort", f"timezone IN {COHORT_TIMEZONES}")


def _attendance():
    op.create_table(
        "attendance_session",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("cohort_id", sa.String(20), sa.ForeignKey("cohort.id"), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("shift", sa.String(10), nullable=False),
        sa.Column("duration_fraction", sa.Numeric(2, 1), nullable=False),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("cohort_id", "session_date", "shift", name="uq_attendance_session_slot"),
        sa.CheckConstraint("shift IN ('manana', 'tarde', 'completa')", name="ck_attendance_session_shift"),
        sa.CheckConstraint(
            "(shift = 'completa' AND duration_fraction = 1) OR (shift IN ('manana','tarde') AND duration_fraction = 0.5)",
            name="ck_attendance_session_fraction",
        ),
    )
    op.create_index("ix_attendance_session_cohort_id", "attendance_session", ["cohort_id"])

    op.create_table(
        "attendance_record",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), sa.ForeignKey("attendance_session.id"), nullable=False),
        sa.Column("enrollment_id", sa.Uuid(), sa.ForeignKey("enrollment.id"), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("modality", sa.String(10)),
        sa.Column("justification", sa.String(15)),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("recorded_by", sa.Uuid(), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id", "enrollment_id", name="uq_attendance_record_session_enrollment"),
        sa.CheckConstraint("status IN ('presente', 'retraso', 'ausente')", name="ck_attendance_record_status"),
        sa.CheckConstraint("justification IS NULL OR justification IN ('justificada', 'no_justificada')", name="ck_attendance_record_justification"),
        sa.CheckConstraint("modality IS NULL OR modality IN ('presencial', 'online')", name="ck_attendance_record_modality"),
        sa.CheckConstraint(RECORD_SHAPE, name="ck_attendance_record_shape"),
    )
    op.create_index("ix_attendance_record_session_id", "attendance_record", ["session_id"])
    op.create_index("ix_attendance_record_enrollment_id", "attendance_record", ["enrollment_id"])

    op.create_table(
        "attendance_record_revision",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("record_id", sa.Uuid(), sa.ForeignKey("attendance_record.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("modality", sa.String(10)),
        sa.Column("justification", sa.String(15)),
        sa.Column("reason", sa.String(300)),
        sa.Column("changed_by", sa.Uuid(), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("record_id", "version", name="uq_attendance_record_revision_version"),
        sa.CheckConstraint(RECORD_SHAPE, name="ck_attendance_record_revision_shape"),
        sa.CheckConstraint("version = 1 OR length(btrim(coalesce(reason, ''))) > 0", name="ck_attendance_record_revision_reason"),
    )
    op.create_index("ix_attendance_record_revision_record_id", "attendance_record_revision", ["record_id"])


def _competencies():
    op.create_table(
        "competency_framework",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("program_id", sa.String(20), sa.ForeignKey("program.id"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("estado", sa.String(10), nullable=False),
        sa.Column("based_on_id", sa.Uuid(), sa.ForeignKey("competency_framework.id")),
        sa.Column("created_by", sa.Uuid(), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("program_id", "version", name="uq_competency_framework_version"),
        sa.CheckConstraint("estado IN ('borrador', 'publicada', 'archivada')", name="ck_competency_framework_estado"),
        sa.CheckConstraint("version >= 1", name="ck_competency_framework_version"),
        sa.CheckConstraint("(estado = 'borrador') = (published_at IS NULL)", name="ck_competency_framework_published_at"),
    )
    op.create_index("ix_competency_framework_program_id", "competency_framework", ["program_id"])
    op.create_index("uq_competency_framework_one_published", "competency_framework", ["program_id"], unique=True, postgresql_where=sa.text("estado = 'publicada'"))

    op.create_table(
        "competency",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("framework_id", sa.Uuid(), sa.ForeignKey("competency_framework.id", ondelete="CASCADE"), nullable=False),
        sa.Column("codigo", sa.String(4), nullable=False),
        sa.Column("nombre", sa.String(160), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("level_1", sa.Text(), nullable=False),
        sa.Column("level_2", sa.Text(), nullable=False),
        sa.Column("level_3", sa.Text(), nullable=False),
        sa.Column("orden", sa.Integer(), nullable=False),
        sa.UniqueConstraint("framework_id", "codigo", name="uq_competency_framework_codigo"),
        sa.CheckConstraint("codigo ~ '^C[1-9][0-9]?$'", name="ck_competency_codigo"),
    )
    op.create_index("ix_competency_framework_id", "competency", ["framework_id"])

    op.create_table(
        "cohort_competency_framework",
        sa.Column("cohort_id", sa.String(20), sa.ForeignKey("cohort.id"), primary_key=True),
        sa.Column("framework_id", sa.Uuid(), sa.ForeignKey("competency_framework.id"), nullable=False),
        sa.Column("assigned_by", sa.Uuid(), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cohort_competency_framework_framework_id", "cohort_competency_framework", ["framework_id"])

    op.create_table(
        "competency_assessment",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("enrollment_id", sa.Uuid(), sa.ForeignKey("enrollment.id"), nullable=False),
        sa.Column("competency_id", sa.Uuid(), sa.ForeignKey("competency.id"), nullable=False),
        sa.Column("level", sa.SmallInteger(), nullable=False),
        sa.Column("evidence", sa.String(500), nullable=False),
        sa.Column("assessed_by", sa.Uuid(), sa.ForeignKey("app_user.id"), nullable=False),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("level BETWEEN 1 AND 3", name="ck_competency_assessment_level"),
        sa.CheckConstraint("length(btrim(evidence)) > 0", name="ck_competency_assessment_evidence"),
    )
    op.create_index("ix_competency_assessment_competency_id", "competency_assessment", ["competency_id"])
    op.create_index("ix_competency_assessment_enrollment_competency", "competency_assessment", ["enrollment_id", "competency_id", "assessed_at"])


def _immutability_triggers():
    """History rows can never be edited or deleted, and a published tree's competencies are frozen."""
    op.execute("""CREATE FUNCTION reject_history_change() RETURNS trigger AS $$
    BEGIN RAISE EXCEPTION '% is append-only', TG_TABLE_NAME; END;
    $$ LANGUAGE plpgsql""")
    for table in ("attendance_record_revision", "competency_assessment"):
        op.execute(f"""CREATE TRIGGER append_only_{table} BEFORE UPDATE OR DELETE ON {table}
        FOR EACH ROW EXECUTE FUNCTION reject_history_change()""")
    op.execute("""CREATE FUNCTION reject_frozen_competency_change() RETURNS trigger AS $$
    BEGIN
      IF (SELECT estado FROM competency_framework WHERE id = COALESCE(OLD.framework_id, NEW.framework_id)) <> 'borrador' THEN
        RAISE EXCEPTION 'Competencies of a published or archived framework are frozen';
      END IF;
      RETURN COALESCE(NEW, OLD);
    END;
    $$ LANGUAGE plpgsql""")
    op.execute("""CREATE TRIGGER frozen_competency BEFORE INSERT OR UPDATE OR DELETE ON competency
    FOR EACH ROW EXECUTE FUNCTION reject_frozen_competency_change()""")


def upgrade():
    _cohort_timezone()
    _attendance()
    _competencies()
    _immutability_triggers()


def downgrade():
    for table in ("competency_assessment", "cohort_competency_framework", "competency", "competency_framework",
                  "attendance_record_revision", "attendance_record", "attendance_session"):
        op.drop_table(table)
    op.execute("DROP FUNCTION reject_frozen_competency_change()")
    op.execute("DROP FUNCTION reject_history_change()")
    op.drop_constraint("ck_cohort_timezone", "cohort")
    op.drop_column("cohort", "timezone")
