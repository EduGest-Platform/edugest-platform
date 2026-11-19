"""RAG knowledge base (ADR-0005): course documents and their chunks, with scope and freshness.

Scope follows the same (scope_type, scope_id) pair as RoleAssignment, so the permission filter can be
applied in SQL before any ranking. Only documents with status 'vigente' and a validity window that
covers the query date may be retrieved.
"""

import uuid
from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base, utcnow

EMBEDDING_DIM = 768  # gemini-embedding-001 with outputDimensionality=768 (ADR-0005)


class KnowledgeDocument(Base):
    """One version of one course document (brief, calendar, criteria...)."""

    __tablename__ = "knowledge_document"
    __table_args__ = (
        CheckConstraint("scope_type IN ('program', 'call', 'cohort')", name="ck_knowledge_document_scope_type"),
        CheckConstraint("status IN ('vigente', 'obsoleto')", name="ck_knowledge_document_status"),
        CheckConstraint("valid_until IS NULL OR valid_until >= valid_from", name="ck_knowledge_document_validity"),
        UniqueConstraint("source_key", "version", name="uq_knowledge_document_source_version"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source_key: Mapped[str] = mapped_column(String(100), index=True)
    title: Mapped[str] = mapped_column(String(200))
    version: Mapped[str] = mapped_column(String(20))
    scope_type: Mapped[str] = mapped_column(String(10))
    scope_id: Mapped[str] = mapped_column(String(30))
    valid_from: Mapped[date] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(10), default="vigente")
    content_hash: Mapped[str] = mapped_column(String(64))  # sha256 hex: skip re-embedding unchanged content
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    chunks: Mapped[list["KnowledgeChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan", passive_deletes=True)


class KnowledgeChunk(Base):
    """A retrievable passage of a document. The embedding may be empty: keyword search still works."""

    __tablename__ = "knowledge_chunk"
    __table_args__ = (
        CheckConstraint("ordinal >= 0", name="ck_knowledge_chunk_ordinal"),
        CheckConstraint("(embedding IS NULL) = (embedding_model IS NULL)", name="ck_knowledge_chunk_embedding_model"),
        UniqueConstraint("document_id", "ordinal", name="uq_knowledge_chunk_document_ordinal"),
    )
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("knowledge_document.id", ondelete="CASCADE"), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    # Vectors from different models cannot be compared, so each chunk records the model that produced it.
    embedding: Mapped[list[float] | None] = mapped_column(Vector(EMBEDDING_DIM))
    embedding_model: Mapped[str | None] = mapped_column(String(60))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    document: Mapped[KnowledgeDocument] = relationship(back_populates="chunks")
