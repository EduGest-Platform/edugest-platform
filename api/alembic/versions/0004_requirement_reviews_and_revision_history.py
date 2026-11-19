"""KAN-128 · requirement reviews and their immutable revision history.

Chained to 0003 because 0002 (F2) does not exist yet. When 0002 lands, set down_revision to '0002' in
whichever of the migrations is merged second, so the history stays linear.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-18
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0004'
down_revision: str | None = '0003'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('requirement_review',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('application_id', sa.Uuid(), nullable=False),
    sa.Column('requirement_ref', sa.String(length=60), nullable=False),
    sa.Column('result', sa.String(length=30), nullable=False),
    sa.Column('reviewer_user_id', sa.Uuid(), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('reason', sa.String(length=500), nullable=True),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("(result = 'pending' AND reviewer_user_id IS NULL AND reviewed_at IS NULL AND reason IS NULL) OR (result <> 'pending' AND reviewer_user_id IS NOT NULL AND reviewed_at IS NOT NULL AND reason IS NOT NULL AND length(btrim(reason)) > 0)", name='ck_requirement_review_completed'),
    sa.CheckConstraint("result IN ('pending', 'met', 'not_met', 'exception_under_review', 'exception_approved')", name='ck_requirement_review_result'),
    sa.ForeignKeyConstraint(['application_id'], ['application.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['reviewer_user_id'], ['app_user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('application_id', 'requirement_ref', name='uq_requirement_review_application_ref')
    )
    op.create_index(op.f('ix_requirement_review_application_id'), 'requirement_review', ['application_id'], unique=False)
    op.create_table('requirement_review_revision',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('review_id', sa.Uuid(), nullable=False),
    sa.Column('revision', sa.Integer(), nullable=False),
    sa.Column('result', sa.String(length=30), nullable=False),
    sa.Column('reviewer_user_id', sa.Uuid(), nullable=False),
    sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('reason', sa.String(length=500), nullable=False),
    sa.CheckConstraint("result IN ('met', 'not_met', 'exception_under_review', 'exception_approved')", name='ck_requirement_review_revision_result'),
    sa.CheckConstraint('length(btrim(reason)) > 0', name='ck_requirement_review_revision_reason'),
    sa.ForeignKeyConstraint(['review_id'], ['requirement_review.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['reviewer_user_id'], ['app_user.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('review_id', 'revision', name='uq_requirement_review_revision_number')
    )
    op.create_index(op.f('ix_requirement_review_revision_review_id'), 'requirement_review_revision', ['review_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_requirement_review_revision_review_id'), table_name='requirement_review_revision')
    op.drop_table('requirement_review_revision')
    op.drop_index(op.f('ix_requirement_review_application_id'), table_name='requirement_review')
    op.drop_table('requirement_review')
