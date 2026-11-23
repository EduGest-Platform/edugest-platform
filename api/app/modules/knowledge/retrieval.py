"""Hybrid retrieval for the RAG assistant (ADR-0005, KAN-130 DA6, KAN-151).

1. Scope first: only chunks of documents inside the caller's KnowledgeScope, with status 'vigente' and a validity
   window that covers the query date, can ever be candidates. The filter is part of the same SQL query as the search.
2. Two rankings: PostgreSQL full-text search in Spanish (always) and pgvector cosine distance (only when there is a
   question vector and the chunk was embedded with the same model). Stems of 4+ letters also match as prefixes, so
   «recetas» (recet) finds «Recetario» (recetari).
3. Reciprocal Rank Fusion merges both rankings without calibrating their scores against each other.
4. Evidence gate: a candidate is kept only if it covers enough of the question's meaningful words, each weighted by
   how rare it is in the corpus (IDF), or, with vectors, if it is similar enough. Nothing kept means: abstain.

Known limit of the keyword-only mode: it does not understand synonyms («fecha límite» vs «entrega»), so it abstains
more. The hybrid mode covers that. Thresholds are tuned with the question bank (python -m app.modules.knowledge.evaluate).
"""

import math
import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy import and_, func, literal_column, or_, select, text
from sqlalchemy.orm import Session

from app.modules.knowledge.embedder import Embedder, EmbeddingError
from app.modules.knowledge.models import KnowledgeChunk, KnowledgeDocument
from app.modules.knowledge.scope import KnowledgeScope

SPANISH = literal_column("'spanish'::regconfig")
SIMPLE = literal_column("'simple'::regconfig")  # question lexemes are already stemmed: do not stem them twice
CANDIDATES = 20  # per ranking, before fusion
RRF_K = 60  # standard Reciprocal Rank Fusion constant
MIN_PREFIX = 4  # shorter stems only match exactly («dia» must not match «diapositiv»)
MIN_COVERAGE = 0.5  # share of the question's IDF-weighted words a chunk must contain (tuned with the bank)
MIN_SIMILARITY = 0.70  # cosine similarity that counts as evidence on its own (vectors only)

_DOCUMENT_FREQUENCY = text("""
    SELECT q.lexeme, count(DISTINCT c.id) AS df
    FROM unnest(CAST(:lexemes AS text[])) AS q(lexeme)
    JOIN knowledge_chunk c ON TRUE
    JOIN knowledge_document d ON d.id = c.document_id
    WHERE d.status = 'vigente' AND EXISTS (
        SELECT 1 FROM unnest(tsvector_to_array(to_tsvector('spanish'::regconfig, c.text))) AS l(lexeme)
        WHERE l.lexeme = q.lexeme OR (length(q.lexeme) >= :min_prefix AND starts_with(l.lexeme, q.lexeme))
    )
    GROUP BY q.lexeme
""")


@dataclass(frozen=True)
class Hit:
    chunk_id: uuid.UUID
    source_key: str
    title: str
    version: str
    valid_from: date
    valid_until: date | None
    ordinal: int
    text: str
    score: float
    coverage: float
    similarity: float | None


@dataclass(frozen=True)
class Retrieval:
    hits: list[Hit]
    mode: str  # "hybrid" (words and vectors) or "keyword" (words only)
    embedding_error: str | None = None

    @property
    def answerable(self) -> bool:
        return bool(self.hits)


@dataclass
class _Candidate:
    chunk: KnowledgeChunk
    document: KnowledgeDocument
    lexemes: frozenset[str]
    rrf: float = 0.0
    similarity: float | None = None


def retrieve(db: Session, scope: KnowledgeScope, question: str, *, today: date,
             embedder: Embedder | None = None, k: int = 3) -> Retrieval:
    if scope.is_empty:
        return Retrieval(hits=[], mode="keyword")
    lexemes = question_lexemes(db, question)
    weights = _idf_weights(db, lexemes)
    candidates: dict[uuid.UUID, _Candidate] = {}
    for position, row in enumerate(_keyword_rows(db, scope, today, lexemes), start=1):
        _candidate(candidates, row).rrf += 1 / (RRF_K + position)

    mode, error = "keyword", None
    if embedder is not None:
        try:
            vector = embedder.embed_query(question)
        except EmbeddingError as exc:
            error = exc.code
        else:
            mode = "hybrid"
            for position, row in enumerate(_semantic_rows(db, scope, today, embedder.model, vector), start=1):
                candidate = _candidate(candidates, row)
                candidate.rrf += 1 / (RRF_K + position)
                candidate.similarity = 1 - float(row.distance)

    hits = []
    for c in candidates.values():
        coverage = _coverage(weights, c.lexemes)
        if coverage >= MIN_COVERAGE or (c.similarity is not None and c.similarity >= MIN_SIMILARITY):
            hits.append(Hit(
                chunk_id=c.chunk.id, source_key=c.document.source_key, title=c.document.title, version=c.document.version,
                valid_from=c.document.valid_from, valid_until=c.document.valid_until, ordinal=c.chunk.ordinal,
                text=c.chunk.text, score=c.rrf, coverage=round(coverage, 3), similarity=c.similarity,
            ))
    hits.sort(key=lambda h: (-h.score, h.source_key, h.ordinal))
    return Retrieval(hits=hits[:k], mode=mode, embedding_error=error)


def question_lexemes(db: Session, question: str) -> list[str]:
    """The question's meaningful words, stemmed in Spanish; stop words such as «el» or «de» disappear."""
    return sorted(set(db.scalar(select(func.tsvector_to_array(func.to_tsvector(SPANISH, question)))) or []))


def _eligible(scope: KnowledgeScope, today: date):
    return and_(
        KnowledgeDocument.status == "vigente",
        KnowledgeDocument.valid_from <= today,
        or_(KnowledgeDocument.valid_until.is_(None), KnowledgeDocument.valid_until >= today),
        or_(
            and_(KnowledgeDocument.scope_type == "cohort", KnowledgeDocument.scope_id.in_(sorted(scope.cohorts))),
            and_(KnowledgeDocument.scope_type == "program", KnowledgeDocument.scope_id.in_(sorted(scope.programs))),
        ),
    )


def _tsvector():
    return func.to_tsvector(SPANISH, KnowledgeChunk.text)


def _tsquery(lexemes: list[str]) -> str:
    """OR of quoted lexemes (prefix match from MIN_PREFIX letters): any shared word makes a chunk a candidate."""
    terms = []
    for lexeme in lexemes:
        quoted = "'" + lexeme.replace("\\", "\\\\").replace("'", "''") + "'"
        terms.append(quoted + ":*" if len(lexeme) >= MIN_PREFIX else quoted)
    return " | ".join(terms)


def _keyword_rows(db: Session, scope: KnowledgeScope, today: date, lexemes: list[str]):
    if not lexemes:
        return []
    query = func.to_tsquery(SIMPLE, _tsquery(lexemes))
    rank = func.ts_rank_cd(_tsvector(), query)
    statement = (
        select(KnowledgeChunk, KnowledgeDocument, func.tsvector_to_array(_tsvector()).label("lexemes"))
        .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
        .where(_eligible(scope, today), _tsvector().op("@@")(query))
        .order_by(rank.desc(), KnowledgeChunk.id)
        .limit(CANDIDATES)
    )
    return db.execute(statement).all()


def _semantic_rows(db: Session, scope: KnowledgeScope, today: date, model: str, vector: list[float]):
    distance = KnowledgeChunk.embedding.cosine_distance(vector)
    statement = (
        select(KnowledgeChunk, KnowledgeDocument, func.tsvector_to_array(_tsvector()).label("lexemes"), distance.label("distance"))
        .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
        .where(_eligible(scope, today), KnowledgeChunk.embedding_model == model)
        .order_by(distance, KnowledgeChunk.id)
        .limit(CANDIDATES)
    )
    return db.execute(statement).all()


def _candidate(candidates: dict[uuid.UUID, _Candidate], row) -> _Candidate:
    chunk = row.KnowledgeChunk
    if chunk.id not in candidates:
        candidates[chunk.id] = _Candidate(chunk=chunk, document=row.KnowledgeDocument, lexemes=frozenset(row.lexemes or []))
    return candidates[chunk.id]


def _idf_weights(db: Session, lexemes: list[str]) -> dict[str, float]:
    """Rare words weigh more. A word that appears in no current chunk gets the highest weight, which pulls the
    coverage down: a question about something the corpus never mentions must not be answered."""
    if not lexemes:
        return {}
    total = db.scalar(
        select(func.count(KnowledgeChunk.id))
        .select_from(KnowledgeChunk)
        .join(KnowledgeDocument, KnowledgeChunk.document_id == KnowledgeDocument.id)
        .where(KnowledgeDocument.status == "vigente")
    ) or 0
    rows = db.execute(_DOCUMENT_FREQUENCY, {"lexemes": lexemes, "min_prefix": MIN_PREFIX})
    frequency = {row.lexeme: row.df for row in rows}
    return {lexeme: math.log((total + 1) / (frequency.get(lexeme, 0) + 1)) + 1 for lexeme in lexemes}


def _matches(lexeme: str, chunk_lexemes: frozenset[str]) -> bool:
    if lexeme in chunk_lexemes:
        return True
    return len(lexeme) >= MIN_PREFIX and any(other.startswith(lexeme) for other in chunk_lexemes)


def _coverage(weights: dict[str, float], chunk_lexemes: frozenset[str]) -> float:
    total = sum(weights.values())
    if not total:
        return 0.0
    return sum(weight for lexeme, weight in weights.items() if _matches(lexeme, chunk_lexemes)) / total
