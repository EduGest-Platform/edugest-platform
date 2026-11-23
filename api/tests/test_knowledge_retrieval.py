"""KAN-130 DA6 / KAN-151: hybrid retrieval with the scope inside the query, against real PostgreSQL."""

import json
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import text

from app.core.config import settings
from app.modules.knowledge.corpus import COHORT_SCOPE
from app.modules.knowledge.embedder import EmbeddingError, FakeEmbedder
from app.modules.knowledge.ingest import run_ingest
from app.modules.knowledge.retrieval import retrieve
from app.modules.knowledge.scope import KnowledgeScope

TODAY = date(2026, 12, 1)  # reference date of the question bank
SCOPE = {
    "A": KnowledgeScope(cohorts=frozenset({COHORT_SCOPE["A"]}), programs=frozenset({"P-IA"})),
    "B": KnowledgeScope(cohorts=frozenset({COHORT_SCOPE["B"]}), programs=frozenset({"P-DATA"})),
}
EMPTY = KnowledgeScope(cohorts=frozenset(), programs=frozenset())
BANK = [json.loads(line) for line in (Path(settings.corpus_path).parent / "questions.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
# q04 shares real words with A1. q01 («fecha límite» vs «Entrega») needs synonyms: a known limit of the
# keyword-only mode that the hybrid mode covers, measured with python -m app.modules.knowledge.evaluate.
RECIPE_DEADLINE = "Si entrego el Recetario un día tarde, ¿me lo aceptan?"


class FailingEmbedder:
    model = "fake-embedding-v1"

    def embed_query(self, text):
        raise EmbeddingError("http_429")


@pytest.fixture
def corpus(db):
    db.execute(text("TRUNCATE knowledge_chunk, knowledge_document"))
    db.commit()
    run_ingest(db, settings.corpus_path)


def keys(result):
    return {hit.source_key for hit in result.hits}


def test_answerable_question_cites_the_right_document(db, corpus):
    result = retrieve(db, SCOPE["A"], RECIPE_DEADLINE, today=TODAY)
    assert result.answerable and result.hits[0].source_key == "A1" and result.mode == "keyword"


@pytest.mark.parametrize("cohort", ["A", "B"])
def test_no_question_of_the_bank_ever_reaches_another_cohort(db, corpus, cohort):
    foreign = {"A": {"B1"}, "B": {"A1", "A2", "A3", "A4", "A5"}}[cohort]
    for question in BANK:
        assert not keys(retrieve(db, SCOPE[cohort], question["question"], today=TODAY)) & foreign, question["id"]


def test_obsolete_document_is_never_retrieved(db, corpus):
    for question in BANK:
        assert "A3" not in keys(retrieve(db, SCOPE["A"], question["question"], today=TODAY)), question["id"]


def test_document_outside_its_validity_window_is_not_retrieved(db, corpus):
    assert "A1" not in keys(retrieve(db, SCOPE["A"], RECIPE_DEADLINE, today=date(2026, 11, 10)))


def test_empty_scope_returns_nothing(db, corpus):
    result = retrieve(db, EMPTY, RECIPE_DEADLINE, today=TODAY)
    assert result.hits == [] and not result.answerable


def test_question_without_meaningful_words_abstains(db, corpus):
    assert not retrieve(db, SCOPE["A"], "¿y de la?", today=TODAY).answerable


def test_hybrid_mode_uses_the_question_vector_and_keeps_the_scope(db):
    db.execute(text("TRUNCATE knowledge_chunk, knowledge_document"))
    db.commit()
    run_ingest(db, settings.corpus_path, embedder=FakeEmbedder())
    fake = FakeEmbedder()
    result = retrieve(db, SCOPE["B"], RECIPE_DEADLINE, today=TODAY, embedder=fake)
    assert result.mode == "hybrid" and fake.query_calls == 1
    assert not keys(result) & {"A1", "A2", "A3", "A4", "A5"}


def test_provider_failure_falls_back_to_keywords(db, corpus):
    result = retrieve(db, SCOPE["A"], RECIPE_DEADLINE, today=TODAY, embedder=FailingEmbedder())
    assert result.mode == "keyword" and result.embedding_error == "http_429"
    assert result.hits[0].source_key == "A1"
