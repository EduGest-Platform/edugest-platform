"""DA4 (ADR-0005): knowledge tables, constraints and vector storage on real PostgreSQL + pgvector."""

import math
from datetime import date

import pytest
from sqlalchemy import delete, inspect, select, text
from sqlalchemy.exc import DataError, IntegrityError, StatementError

from app.core.db import engine
from app.modules.knowledge.models import EMBEDDING_DIM, KnowledgeChunk, KnowledgeDocument

MODEL = "gemini-embedding-001"


@pytest.fixture(autouse=True)
def _empty_knowledge(db):
    db.execute(delete(KnowledgeDocument))
    db.commit()
    yield
    db.rollback()
    db.execute(delete(KnowledgeDocument))
    db.commit()


def unit_vector(position: int) -> list[float]:
    values = [0.0] * EMBEDDING_DIM
    values[position] = 1.0
    return values


def document(**over) -> KnowledgeDocument:
    fields = dict(
        source_key="calendario-cohorte", title="Calendario de la cohorte (sintético)", version="v2",
        scope_type="cohort", scope_id="COH-IA-2026A", valid_from=date(2026, 11, 1), valid_until=date(2026, 12, 22),
        status="vigente", content_hash="0" * 64,
    )
    fields.update(over)
    return KnowledgeDocument(**fields)


def test_tables_and_vector_column_exist():
    columns = {c["name"]: c for c in inspect(engine).get_columns("knowledge_chunk")}
    assert "embedding" in columns
    with engine.connect() as conn:
        assert conn.scalar(text("SELECT count(*) FROM pg_extension WHERE extname = 'vector'")) == 1
        assert conn.scalar(text("SELECT format_type(atttypid, atttypmod) FROM pg_attribute "
                                "WHERE attrelid = 'knowledge_chunk'::regclass AND attname = 'embedding'")) == "vector(768)"


def test_document_defaults_mark_synthetic_and_current(db):
    doc = document()
    db.add(doc)
    db.commit()
    assert doc.is_synthetic is True
    assert doc.status == "vigente"
    assert doc.created_at is not None and doc.updated_at is not None


def test_vector_round_trip_and_cosine_distance(db):
    doc = document()
    doc.chunks = [
        KnowledgeChunk(ordinal=0, text="Clases presenciales lunes y martes.", embedding=unit_vector(0), embedding_model=MODEL),
        KnowledgeChunk(ordinal=1, text="Tutorías los viernes.", embedding=unit_vector(1), embedding_model=MODEL),
    ]
    db.add(doc)
    db.commit()
    rows = db.execute(
        select(KnowledgeChunk.ordinal, KnowledgeChunk.embedding.cosine_distance(unit_vector(0)).label("distance"))
        .order_by("distance")
    ).all()
    assert [r.ordinal for r in rows] == [0, 1]
    assert math.isclose(rows[0].distance, 0.0, abs_tol=1e-6)
    assert math.isclose(rows[1].distance, 1.0, abs_tol=1e-6)
    stored = db.scalar(select(KnowledgeChunk.embedding).where(KnowledgeChunk.ordinal == 0))
    assert len(stored) == EMBEDDING_DIM


def test_chunk_without_embedding_is_allowed_for_keyword_fallback(db):
    doc = document()
    doc.chunks = [KnowledgeChunk(ordinal=0, text="Festivos: 7 y 8 de diciembre.")]
    db.add(doc)
    db.commit()
    found = db.scalar(
        select(KnowledgeChunk.text).where(text("to_tsvector('spanish', knowledge_chunk.text) @@ plainto_tsquery('spanish', 'festivos')"))
    )
    assert found == "Festivos: 7 y 8 de diciembre."


@pytest.mark.parametrize(
    "over",
    [
        {"status": "borrador"},
        {"scope_type": "global"},
        {"valid_from": date(2026, 12, 1), "valid_until": date(2026, 11, 1)},
    ],
)
def test_document_constraints_reject_invalid_rows(db, over):
    db.add(document(**over))
    with pytest.raises(IntegrityError):
        db.commit()


def test_same_source_and_version_cannot_be_stored_twice(db):
    db.add(document())
    db.commit()
    db.add(document(title="Otra copia"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
    db.add(document(version="v3"))
    db.commit()


def test_embedding_and_model_must_be_set_together(db):
    doc = document()
    doc.chunks = [KnowledgeChunk(ordinal=0, text="Sin modelo", embedding=unit_vector(0))]
    db.add(doc)
    with pytest.raises(IntegrityError):
        db.commit()


def test_wrong_vector_dimension_is_rejected(db):
    doc = document()
    doc.chunks = [KnowledgeChunk(ordinal=0, text="Dimensión incorrecta", embedding=[1.0, 0.0, 0.0], embedding_model=MODEL)]
    db.add(doc)
    with pytest.raises((DataError, StatementError)):
        db.commit()


def test_duplicate_ordinal_in_same_document_is_rejected(db):
    doc = document()
    doc.chunks = [KnowledgeChunk(ordinal=0, text="Uno"), KnowledgeChunk(ordinal=0, text="Otro")]
    db.add(doc)
    with pytest.raises(IntegrityError):
        db.commit()


def test_deleting_a_document_deletes_its_chunks(db):
    doc = document()
    doc.chunks = [KnowledgeChunk(ordinal=0, text="Fragmento")]
    db.add(doc)
    db.commit()
    db.execute(delete(KnowledgeDocument).where(KnowledgeDocument.id == doc.id))
    db.commit()
    assert db.scalar(select(KnowledgeChunk.id)) is None
