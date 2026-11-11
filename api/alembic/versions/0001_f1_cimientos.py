"""F1 · cimientos: identidad, catálogo, admisión, matrícula y auditoría de solo inserción.

Generada con autogenerate y revisada a mano; añade el trigger que impide UPDATE/DELETE en audit_event.

Revision ID: 0001
Revises: 
Create Date: 2026-11-08 13:09:04.965284
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0001'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('person',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('display_name', sa.String(length=120), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('legacy_ref', sa.String(length=20), nullable=True),
    sa.Column('is_synthetic', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('legacy_ref')
    )
    op.create_index(op.f('ix_person_email'), 'person', ['email'], unique=True)
    op.create_table('program',
    sa.Column('id', sa.String(length=20), nullable=False),
    sa.Column('nombre', sa.String(length=120), nullable=False),
    sa.Column('descripcion', sa.Text(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('app_user',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('display_name', sa.String(length=120), nullable=False),
    sa.Column('password_hash', sa.String(length=200), nullable=False),
    sa.Column('person_id', sa.Uuid(), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['person_id'], ['person.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('person_id')
    )
    op.create_index(op.f('ix_app_user_email'), 'app_user', ['email'], unique=True)
    op.create_table('call',
    sa.Column('id', sa.String(length=30), nullable=False),
    sa.Column('program_id', sa.String(length=20), nullable=False),
    sa.Column('nombre', sa.String(length=160), nullable=False),
    sa.Column('codigo_prefix', sa.String(length=10), nullable=False),
    sa.Column('opens_on', sa.Date(), nullable=False),
    sa.Column('closes_on', sa.Date(), nullable=False),
    sa.Column('plazas', sa.Integer(), nullable=False),
    sa.Column('estado', sa.String(length=10), nullable=False),
    sa.Column('next_seq', sa.Integer(), nullable=False),
    sa.CheckConstraint("estado IN ('abierta','cerrada')", name='ck_call_estado'),
    sa.ForeignKeyConstraint(['program_id'], ['program.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('codigo_prefix')
    )
    op.create_index(op.f('ix_call_program_id'), 'call', ['program_id'], unique=False)
    op.create_table('application',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('codigo', sa.String(length=20), nullable=False),
    sa.Column('legacy_ref', sa.String(length=20), nullable=True),
    sa.Column('person_id', sa.Uuid(), nullable=False),
    sa.Column('call_id', sa.String(length=30), nullable=False),
    sa.Column('stage', sa.String(length=40), nullable=False),
    sa.Column('motivacion', sa.Text(), nullable=False),
    sa.Column('disponibilidad', sa.String(length=20), nullable=False),
    sa.Column('acepta_datos_sinteticos', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("stage IN ('enviada', 'requisitos_en_revision', 'convocada', 'evaluacion_en_curso', 'pendiente_decision_humana', 'admitida', 'lista_espera', 'no_admitida', 'retirada')", name='ck_application_stage'),
    sa.ForeignKeyConstraint(['call_id'], ['call.id'], ),
    sa.ForeignKeyConstraint(['person_id'], ['person.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('codigo'),
    sa.UniqueConstraint('legacy_ref'),
    sa.UniqueConstraint('person_id', 'call_id', name='uq_application_person_call')
    )
    op.create_index(op.f('ix_application_call_id'), 'application', ['call_id'], unique=False)
    op.create_index(op.f('ix_application_person_id'), 'application', ['person_id'], unique=False)
    op.create_table('audit_event',
    sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
    sa.Column('at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('actor_user_id', sa.Uuid(), nullable=True),
    sa.Column('actor_roles', sa.String(length=200), nullable=False),
    sa.Column('action', sa.String(length=60), nullable=False),
    sa.Column('target_type', sa.String(length=40), nullable=False),
    sa.Column('target_id', sa.String(length=60), nullable=True),
    sa.Column('meta', sa.JSON(), nullable=False),
    sa.ForeignKeyConstraint(['actor_user_id'], ['app_user.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_event_action'), 'audit_event', ['action'], unique=False)
    op.create_index(op.f('ix_audit_event_at'), 'audit_event', ['at'], unique=False)
    op.create_table('auth_session',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['app_user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token_hash')
    )
    op.create_index(op.f('ix_auth_session_user_id'), 'auth_session', ['user_id'], unique=False)
    op.create_table('cohort',
    sa.Column('id', sa.String(length=20), nullable=False),
    sa.Column('program_id', sa.String(length=20), nullable=False),
    sa.Column('call_id', sa.String(length=30), nullable=True),
    sa.Column('nombre', sa.String(length=160), nullable=False),
    sa.Column('inicio', sa.Date(), nullable=False),
    sa.Column('fin', sa.Date(), nullable=False),
    sa.ForeignKeyConstraint(['call_id'], ['call.id'], ),
    sa.ForeignKeyConstraint(['program_id'], ['program.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cohort_program_id'), 'cohort', ['program_id'], unique=False)
    op.create_table('role_assignment',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('role', sa.String(length=30), nullable=False),
    sa.Column('scope_type', sa.String(length=10), nullable=False),
    sa.Column('scope_id', sa.String(length=40), nullable=True),
    sa.Column('granted_by', sa.Uuid(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.CheckConstraint("(scope_type = 'global') = (scope_id IS NULL)", name='ck_role_assignment_scope_id'),
    sa.CheckConstraint("role IN ('admin', 'captacion', 'seleccion', 'docente', 'coordinacion')", name='ck_role_assignment_role'),
    sa.CheckConstraint("scope_type IN ('global', 'program', 'call', 'cohort')", name='ck_role_assignment_scope_type'),
    sa.ForeignKeyConstraint(['granted_by'], ['app_user.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['app_user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'role', 'scope_type', 'scope_id', name='uq_role_assignment')
    )
    op.create_index(op.f('ix_role_assignment_user_id'), 'role_assignment', ['user_id'], unique=False)
    op.create_table('application_event',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('application_id', sa.Uuid(), nullable=False),
    sa.Column('tipo', sa.String(length=20), nullable=False),
    sa.Column('canal', sa.String(length=20), nullable=True),
    sa.Column('resumen', sa.String(length=500), nullable=False),
    sa.Column('actor_user_id', sa.Uuid(), nullable=True),
    sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("canal IS NULL OR canal IN ('email', 'telefono', 'presencial', 'videollamada')", name='ck_application_event_canal'),
    sa.CheckConstraint("tipo IN ('creada', 'contacto', 'nota', 'recordatorio', 'cambio_etapa')", name='ck_application_event_tipo'),
    sa.ForeignKeyConstraint(['actor_user_id'], ['app_user.id'], ),
    sa.ForeignKeyConstraint(['application_id'], ['application.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_application_event_application_id'), 'application_event', ['application_id'], unique=False)
    op.create_table('enrollment',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('person_id', sa.Uuid(), nullable=False),
    sa.Column('cohort_id', sa.String(length=20), nullable=False),
    sa.Column('application_id', sa.Uuid(), nullable=True),
    sa.Column('estado', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("estado IN ('activa','finalizada','baja_voluntaria')", name='ck_enrollment_estado'),
    sa.ForeignKeyConstraint(['application_id'], ['application.id'], ),
    sa.ForeignKeyConstraint(['cohort_id'], ['cohort.id'], ),
    sa.ForeignKeyConstraint(['person_id'], ['person.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('person_id', 'cohort_id', name='uq_enrollment_person_cohort')
    )
    op.create_index(op.f('ix_enrollment_cohort_id'), 'enrollment', ['cohort_id'], unique=False)
    op.create_index(op.f('ix_enrollment_person_id'), 'enrollment', ['person_id'], unique=False)

    # Append-only audit trail: any UPDATE or DELETE on audit_event fails.
    op.execute(
        """
        CREATE FUNCTION audit_event_append_only() RETURNS trigger AS $$
        BEGIN
          RAISE EXCEPTION 'audit_event es de solo inserción';
        END;
        $$ LANGUAGE plpgsql;
        CREATE TRIGGER trg_audit_event_append_only BEFORE UPDATE OR DELETE ON audit_event
          FOR EACH ROW EXECUTE FUNCTION audit_event_append_only();
        """
    )

def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_audit_event_append_only ON audit_event; DROP FUNCTION IF EXISTS audit_event_append_only();")
    op.drop_index(op.f('ix_enrollment_person_id'), table_name='enrollment')
    op.drop_index(op.f('ix_enrollment_cohort_id'), table_name='enrollment')
    op.drop_table('enrollment')
    op.drop_index(op.f('ix_application_event_application_id'), table_name='application_event')
    op.drop_table('application_event')
    op.drop_index(op.f('ix_role_assignment_user_id'), table_name='role_assignment')
    op.drop_table('role_assignment')
    op.drop_index(op.f('ix_cohort_program_id'), table_name='cohort')
    op.drop_table('cohort')
    op.drop_index(op.f('ix_auth_session_user_id'), table_name='auth_session')
    op.drop_table('auth_session')
    op.drop_index(op.f('ix_audit_event_at'), table_name='audit_event')
    op.drop_index(op.f('ix_audit_event_action'), table_name='audit_event')
    op.drop_table('audit_event')
    op.drop_index(op.f('ix_application_person_id'), table_name='application')
    op.drop_index(op.f('ix_application_call_id'), table_name='application')
    op.drop_table('application')
    op.drop_index(op.f('ix_call_program_id'), table_name='call')
    op.drop_table('call')
    op.drop_index(op.f('ix_app_user_email'), table_name='app_user')
    op.drop_table('app_user')
    op.drop_table('program')
    op.drop_index(op.f('ix_person_email'), table_name='person')
    op.drop_table('person')
