"""RAG · knowledge base: documents and chunks with scope, freshness and 768-dimension vectors (ADR-0005, DA4).

Chained to 0001 because 0002 (F2) does not exist yet. When 0002 lands, set down_revision to '0002' in
whichever of the two is merged second, so the history stays linear.

The vector extension is created here and is not dropped on downgrade: it is database-wide and other
objects may depend on it.

Revision ID: 0003
Revises: 0001
Create Date: 2026-11-18
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector


revision: str = '0003'
down_revision: str | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table('knowledge_document',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('source_key', sa.String(length=100), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('version', sa.String(length=20), nullable=False),
    sa.Column('scope_type', sa.String(length=10), nullable=False),
    sa.Column('scope_id', sa.String(length=30), nullable=False),
    sa.Column('valid_from', sa.Date(), nullable=False),
    sa.Column('valid_until', sa.Date(), nullable=True),
    sa.Column('status', sa.String(length=10), nullable=False),
    sa.Column('content_hash', sa.String(length=64), nullable=False),
    sa.Column('is_synthetic', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("scope_type IN ('program', 'call', 'cohort')", name='ck_knowledge_document_scope_type'),
    sa.CheckConstraint("status IN ('vigente', 'obsoleto')", name='ck_knowledge_document_status'),
    sa.CheckConstraint('valid_until IS NULL OR valid_until >= valid_from', name='ck_knowledge_document_validity'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('source_key', 'version', name='uq_knowledge_document_source_version')
    )
    op.create_index(op.f('ix_knowledge_document_source_key'), 'knowledge_document', ['source_key'], unique=False)
    op.create_table('knowledge_chunk',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('document_id', sa.Uuid(), nullable=False),
    sa.Column('ordinal', sa.Integer(), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('embedding', Vector(dim=768), nullable=True),
    sa.Column('embedding_model', sa.String(length=60), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('(embedding IS NULL) = (embedding_model IS NULL)', name='ck_knowledge_chunk_embedding_model'),
    sa.CheckConstraint('ordinal >= 0', name='ck_knowledge_chunk_ordinal'),
    sa.ForeignKeyConstraint(['document_id'], ['knowledge_document.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('document_id', 'ordinal', name='uq_knowledge_chunk_document_ordinal')
    )
    op.create_index(op.f('ix_knowledge_chunk_document_id'), 'knowledge_chunk', ['document_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_knowledge_chunk_document_id'), table_name='knowledge_chunk')
    op.drop_table('knowledge_chunk')
    op.drop_index(op.f('ix_knowledge_document_source_key'), table_name='knowledge_document')
    op.drop_table('knowledge_document')
