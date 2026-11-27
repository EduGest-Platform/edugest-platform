"""selection appointments

Revision ID: 0023_selection_appointments
Revises: 0022
Create Date: 2026-11-26 16:01:57.097310
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0023_selection_appointments'
down_revision: str | None = '0022'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'selection_appointment',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('application_id', sa.Uuid(), nullable=False),
        sa.Column('previous_id', sa.Uuid(), nullable=True),
        sa.Column('kind', sa.String(length=24), nullable=False),
        sa.Column('state', sa.String(length=12), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('location', sa.String(length=250), nullable=True),
        sa.Column('created_by', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('recorded_by', sa.Uuid(), nullable=True),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('conclusions', sa.String(length=1000), nullable=True),
        sa.Column('assessment', sa.String(length=500), nullable=True),
        sa.CheckConstraint(
            "num_nonnulls(recorded_at, recorded_by) = CASE WHEN state IN ('attended', 'no_show') THEN 2 ELSE 0 END",
            name='ck_selection_appointment_recorded',
        ),
        sa.CheckConstraint("kind IN ('group_day', 'individual_interview')", name='ck_selection_appointment_kind'),
        sa.CheckConstraint("state = 'attended' OR (conclusions IS NULL AND assessment IS NULL)", name='ck_selection_appointment_notes'),
        sa.CheckConstraint("state IN ('scheduled', 'attended', 'no_show', 'rescheduled')", name='ck_selection_appointment_state'),
        sa.ForeignKeyConstraint(['application_id'], ['application.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['created_by'], ['app_user.id']),
        sa.ForeignKeyConstraint(['previous_id'], ['selection_appointment.id']),
        sa.ForeignKeyConstraint(['recorded_by'], ['app_user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('previous_id'),
    )
    op.create_index(op.f('ix_selection_appointment_application_id'), 'selection_appointment', ['application_id'], unique=False)
    op.create_index(
        'uq_selection_appointment_scheduled_kind', 'selection_appointment', ['application_id', 'kind'],
        unique=True, postgresql_where=sa.text("state = 'scheduled'"),
    )


def downgrade() -> None:
    op.drop_table('selection_appointment')
