"""KAN-130 part B: vectors in the ingest, with the offline FakeEmbedder and real PostgreSQL."""

import shutil
from pathlib import Path

import pytest
from sqlalchemy import select, text

from app.core.config import settings
from app.modules.audit.models import AuditEvent
from app.modules.knowledge.embedder import EmbeddingError, FakeEmbedder
from app.modules.knowledge.ingest import run_ingest
from app.modules.knowledge.models import EMBEDDING_DIM, KnowledgeChunk


@pytest.fixture(autouse=True)
def empty_knowledge(db):
    db.execute(text("TRUNCATE knowledge_chunk, knowledge_document"))
    db.commit()


@pytest.fixture
def corpus(tmp_path):
    target = tmp_path / "corpus"
    shutil.copytree(settings.corpus_path, target)
    return target


class FailingEmbedder:
    model = "fake-embedding-v1"
    dimensions = EMBEDDING_DIM

    def embed_documents(self, passages):
        raise EmbeddingError("http_429")


def chunks(db):
    db.expire_all()
    return list(db.scalars(select(KnowledgeChunk)))


def test_first_ingest_embeds_every_chunk(db, corpus):
    fake = FakeEmbedder()
    results = run_ingest(db, str(corpus), embedder=fake)
    stored = chunks(db)
    assert stored and all(c.embedding_model == fake.model and len(c.embedding) == EMBEDDING_DIM for c in stored)
    assert all(r.embedded and r.embedding_error is None for r in results)
    assert fake.calls == len(results)
    assert db.scalar(select(AuditEvent).where(AuditEvent.action == "knowledge.document.embedded")) is not None


def test_rerun_without_changes_makes_no_calls(db, corpus):
    run_ingest(db, str(corpus), embedder=FakeEmbedder())
    again = FakeEmbedder()
    results = run_ingest(db, str(corpus), embedder=again)
    assert again.calls == 0 and {r.action for r in results} == {"unchanged"}


def test_changing_one_document_only_embeds_that_document(db, corpus):
    run_ingest(db, str(corpus), embedder=FakeEmbedder())
    document = next(Path(corpus).glob("*.md"))
    document.write_text(document.read_text(encoding="utf-8") + "\n\nPárrafo nuevo sintético.\n", encoding="utf-8")
    fake = FakeEmbedder()
    results = run_ingest(db, str(corpus), embedder=fake)
    assert fake.calls == 1 and [r.action for r in results].count("updated") == 1
    assert all(c.embedding_model for c in chunks(db))


def test_new_model_reembeds_without_changing_content(db, corpus):
    run_ingest(db, str(corpus), embedder=FakeEmbedder())
    newer = FakeEmbedder(model="fake-embedding-v2")
    results = run_ingest(db, str(corpus), embedder=newer)
    assert newer.calls == len(results) and {r.action for r in results} == {"unchanged"}
    assert {c.embedding_model for c in chunks(db)} == {"fake-embedding-v2"}


def test_provider_failure_still_stores_the_text(db, corpus):
    results = run_ingest(db, str(corpus), embedder=FailingEmbedder())
    stored = chunks(db)
    assert stored and all(c.embedding is None and c.embedding_model is None for c in stored)
    assert {r.action for r in results} == {"created"} and {r.embedding_error for r in results} == {"http_429"}
    assert all(not r.embedded for r in results)


def test_running_without_provider_keeps_existing_vectors(db, corpus):
    run_ingest(db, str(corpus), embedder=FakeEmbedder())
    results = run_ingest(db, str(corpus), embedder=None)
    assert {r.action for r in results} == {"unchanged"} and all(r.embedded for r in results)
    assert all(c.embedding_model == "fake-embedding-v1" for c in chunks(db))


def test_dry_run_with_provider_saves_nothing(db, corpus):
    run_ingest(db, str(corpus), dry_run=True, embedder=FakeEmbedder())
    assert chunks(db) == []
