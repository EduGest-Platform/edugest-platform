"""Ingests one course document into the RAG knowledge base (KAN-130).

The pipeline does not know where documents come from (see corpus.py) and never commits: the caller decides,
one transaction per document, so a failure never leaves half a document behind and a dry run is a rollback.
Steps: personal data check on title and text (fail closed) -> chunking -> create, update or skip by content
hash -> audit. Chunks are built from title and text, so the hash covers both: a title change rewrites them.
Embeddings come in a later increment; until then chunks are stored without a vector (keyword search works).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import audit
from app.modules.knowledge.chunking import split_into_chunks
from app.modules.knowledge.corpus import SourceDocument
from app.modules.knowledge.models import KnowledgeChunk, KnowledgeDocument
from app.modules.knowledge.privacy import find_personal_data

TARGET = "knowledge_document"
METADATA_FIELDS = ("title", "scope_type", "scope_id", "valid_from", "valid_until", "status", "is_synthetic")


@dataclass(frozen=True)
class IngestResult:
    """What happened to one document. `reason` explains rejections and failures, never with document content."""

    source_key: str
    version: str
    action: str  # created | updated | unchanged | rejected | retired | failed
    title: str | None = None
    scope_id: str | None = None
    status: str | None = None
    valid_from: date | None = None
    valid_until: date | None = None
    maintained_by: str | None = None
    chunks: int | None = None
    embedded: bool = False
    reason: str | None = None


def content_hash(title: str, text: str) -> str:
    """Fingerprint of everything the chunks are built from."""
    return hashlib.sha256(f"{title}\n{text}".encode("utf-8")).hexdigest()


def ingest_document(db: Session, doc: SourceDocument, known_names: list[str]) -> IngestResult:
    """Creates, updates or skips one document version. Flushes but never commits."""
    findings = find_personal_data(f"{doc.title}\n{doc.text}", known_names)
    if findings:
        return _reject(db, doc, "personal_data", f"personal data: {', '.join(findings)}", kinds=findings)
    chunks = split_into_chunks(doc.title, doc.text)
    if not chunks:
        return _reject(db, doc, "no_content", "no content to index")

    digest = content_hash(doc.title, doc.text)
    stored = db.scalar(
        select(KnowledgeDocument).where(KnowledgeDocument.source_key == doc.source_key, KnowledgeDocument.version == doc.version)
    )
    if stored is None:
        stored, action = KnowledgeDocument(source_key=doc.source_key, version=doc.version), "created"
        db.add(stored)
    elif stored.content_hash == digest and _same_metadata(stored, doc):
        return _result(doc, "unchanged", stored)
    else:
        action = "updated"

    for field in METADATA_FIELDS:
        setattr(stored, field, getattr(doc, field))
    if stored.content_hash != digest:
        # Set the hash before any flush: content_hash is NOT NULL and _replace_chunks flushes.
        stored.content_hash = digest
        _replace_chunks(db, stored, chunks)
    db.flush()
    audit.record(
        db, None, f"knowledge.document.{action}", TARGET, str(stored.id),
        source_key=doc.source_key, version=doc.version, status=doc.status, chunks=len(stored.chunks),
    )
    return _result(doc, action, stored)


def retire_missing(db: Session, loaded_versions: dict[str, str], protected_keys: set[str]) -> list[IngestResult]:
    """Marks as obsolete (never deletes) current documents that left the corpus or were replaced by a new version.

    Protected keys are left alone: an unreadable entry, or a new version that was rejected or failed, must never
    retire the version that is still usable.
    """
    results = []
    current = db.scalars(
        select(KnowledgeDocument).where(KnowledgeDocument.status == "vigente").order_by(KnowledgeDocument.source_key, KnowledgeDocument.version)
    )
    for stored in current:
        if stored.source_key in protected_keys or loaded_versions.get(stored.source_key) == stored.version:
            continue
        stored.status = "obsoleto"
        audit.record(db, None, "knowledge.document.retired", TARGET, str(stored.id), source_key=stored.source_key, version=stored.version)
        results.append(
            IngestResult(
                stored.source_key, stored.version, "retired", title=stored.title, scope_id=stored.scope_id, status=stored.status,
                valid_from=stored.valid_from, valid_until=stored.valid_until, chunks=len(stored.chunks), embedded=_embedded(stored),
            )
        )
    db.flush()
    return results


def _same_metadata(stored: KnowledgeDocument, doc: SourceDocument) -> bool:
    return all(getattr(stored, field) == getattr(doc, field) for field in METADATA_FIELDS)


def _replace_chunks(db: Session, stored: KnowledgeDocument, chunks: list[str]) -> None:
    # Delete first, then insert: one flush could insert before deleting and break the (document_id, ordinal) unique key.
    stored.chunks.clear()
    db.flush()
    stored.chunks.extend(KnowledgeChunk(ordinal=i, text=text) for i, text in enumerate(chunks))


def _embedded(stored: KnowledgeDocument) -> bool:
    return bool(stored.chunks) and all(chunk.embedding_model for chunk in stored.chunks)


def _reject(db: Session, doc: SourceDocument, code: str, reason: str, **meta) -> IngestResult:
    audit.record(db, None, "knowledge.document.rejected", TARGET, doc.source_key, source_key=doc.source_key, version=doc.version, reason=code, **meta)
    db.flush()
    # The title may hold the rejected data: it is not carried into the report.
    return _result(doc, "rejected", None, reason=reason, show_title=False)


def _result(doc: SourceDocument, action: str, stored: KnowledgeDocument | None, reason: str | None = None, show_title: bool = True) -> IngestResult:
    return IngestResult(
        doc.source_key, doc.version, action, title=doc.title if show_title else None, scope_id=doc.scope_id, status=doc.status,
        valid_from=doc.valid_from, valid_until=doc.valid_until, maintained_by=doc.maintained_by,
        chunks=len(stored.chunks) if stored is not None else None,
        embedded=_embedded(stored) if stored is not None else False, reason=reason,
    )
