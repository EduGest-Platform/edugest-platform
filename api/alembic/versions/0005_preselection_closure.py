"""KAN-153 · end of pre-selection: per-call silence policy, contact attempt results and human decision history.

Additive and reversible. Chained to 0004; 0002 (F2) does not exist yet. When 0002 lands, keep this migration
after 0004 so the history stays linear.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-18
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0005'
down_revision: str | None = '0004'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

STAGES = "('enviada', 'requisitos_en_revision', 'convocada', 'evaluacion_en_curso', 'pendiente_decision_humana', 'admitida', 'lista_espera', 'no_admitida', 'retirada')"


def upgrade() -> None:
    op.add_column('call', sa.Column('silence_days', sa.Integer(), server_default=sa.text('30'), nullable=False))
    op.add_column('call', sa.Column('silence_max_contacts', sa.Integer(), server_default=sa.text('4'), nullable=False))
    op.create_check_constraint('ck_call_silence_days', 'call', 'silence_days BETWEEN 1 AND 365')
    op.create_check_constraint('ck_call_silence_max_contacts', 'call', 'silence_max_contacts BETWEEN 1 AND 20')

    op.add_column('application_event', sa.Column('resultado', sa.String(length=20), nullable=True))
    op.create_check_constraint(
        'ck_application_event_resultado', 'application_event',
        "resultado IS NULL OR (tipo = 'contacto' AND resultado IN ('respondida', 'sin_respuesta'))",
    )

    op.create_table('preselection_decision',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('application_id', sa.Uuid(), nullable=False),
    sa.Column('decision', sa.String(length=30), nullable=False),
    sa.Column('from_stage', sa.String(length=40), nullable=False),
    sa.Column('to_stage', sa.String(length=40), nullable=False),
    sa.Column('reason', sa.String(length=500), nullable=False),
    sa.Column('actor_user_id', sa.Uuid(), nullable=False),
    sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('evidence', sa.JSON(), nullable=False),
    sa.CheckConstraint("decision IN ('convocada', 'retirada_expresa', 'silencio_confirmado', 'silencio_reprogramado')", name='ck_preselection_decision_decision'),
    sa.CheckConstraint(f"from_stage IN {STAGES} AND to_stage IN {STAGES}", name='ck_preselection_decision_stages'),
    sa.CheckConstraint('length(btrim(reason)) > 0', name='ck_preselection_decision_reason'),
    sa.ForeignKeyConstraint(['actor_user_id'], ['app_user.id'], ),
    sa.ForeignKeyConstraint(['application_id'], ['application.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_preselection_decision_application_id'), 'preselection_decision', ['application_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_preselection_decision_application_id'), table_name='preselection_decision')
    op.drop_table('preselection_decision')
    op.drop_constraint('ck_application_event_resultado', 'application_event', type_='check')
    op.drop_column('application_event', 'resultado')
    op.drop_constraint('ck_call_silence_max_contacts', 'call', type_='check')
    op.drop_constraint('ck_call_silence_days', 'call', type_='check')
    op.drop_column('call', 'silence_max_contacts')
    op.drop_column('call', 'silence_days')
