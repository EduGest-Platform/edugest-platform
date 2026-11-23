"""KAN-48 · end of selection: human admission decisions that can create the enrollment.

Additive and reversible: one new table, no change to existing ones. Chained after 0009 (current head of dev
at the time of writing). If another branch adds a 0010 first, renumber this file and its ``revision`` when
rebasing: ``alembic heads`` must show a single head.

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-23
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0010'
down_revision: str | None = '0009'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STAGES = "('enviada', 'requisitos_en_revision', 'convocada', 'evaluacion_en_curso', 'pendiente_decision_humana', 'admitida', 'lista_espera', 'no_admitida', 'retirada')"


def upgrade() -> None:
    op.create_table('selection_decision',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('application_id', sa.Uuid(), nullable=False),
    sa.Column('decision', sa.String(length=20), nullable=False),
    sa.Column('from_stage', sa.String(length=40), nullable=False),
    sa.Column('to_stage', sa.String(length=40), nullable=False),
    sa.Column('reason', sa.String(length=500), nullable=False),
    sa.Column('actor_user_id', sa.Uuid(), nullable=False),
    sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('cohort_id', sa.String(length=20), nullable=True),
    sa.Column('enrollment_id', sa.Uuid(), nullable=True),
    sa.CheckConstraint("decision IN ('admitida', 'lista_espera', 'no_admitida')", name='ck_selection_decision_decision'),
    sa.CheckConstraint(f"from_stage IN {STAGES} AND to_stage IN {STAGES}", name='ck_selection_decision_stages'),
    sa.CheckConstraint('length(btrim(reason)) > 0', name='ck_selection_decision_reason'),
    sa.CheckConstraint("(decision = 'admitida') = (cohort_id IS NOT NULL AND enrollment_id IS NOT NULL)", name='ck_selection_decision_enrollment'),
    sa.ForeignKeyConstraint(['actor_user_id'], ['app_user.id'], ),
    sa.ForeignKeyConstraint(['application_id'], ['application.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['cohort_id'], ['cohort.id'], ),
    sa.ForeignKeyConstraint(['enrollment_id'], ['enrollment.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_selection_decision_application_id'), 'selection_decision', ['application_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_selection_decision_application_id'), table_name='selection_decision')
    op.drop_table('selection_decision')
