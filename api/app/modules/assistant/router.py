"""RAG assistant over the course documents (ADR-0005, KAN-130 DA6, KAN-151).

The scope comes from the server (knowledge_scope), never from the question. The answer is extractive: the passage
found, with its citation, or an explicit abstention. The audit keeps the outcome, the search mode and the documents
used, never the text of the question.
"""

from datetime import date
from zoneinfo import ZoneInfo

from fastapi import APIRouter, status

from app.core import audit
from app.core.db import utcnow
from app.core.deps import DB, CurrentPrincipal
from app.core.errors import UserFacingError
from app.modules.assistant import records
from app.modules.assistant.schemas import AskIn, AskOut, Citation, RecordSource
from app.modules.catalog.models import Cohort
from app.modules.knowledge.embedder import GeminiEmbedder
from app.modules.knowledge.ingest import build_embedder
from app.modules.knowledge.retrieval import Hit, retrieve
from app.modules.knowledge.scope import KnowledgeScope, knowledge_scope

router = APIRouter(prefix="/assistant", tags=["assistant"])

MADRID = ZoneInfo("Europe/Madrid")
NO_SOURCE = "No consta en la documentación de tu curso. Consulta con tu equipo docente."
CHOOSE_COHORT = "Tienes varias cohortes. Indica cuál (por ejemplo, COH-IA) para consultar los registros."


def today() -> date:
    """The cut-off date for document validity: today in the platform's time zone (tests replace it)."""
    return utcnow().astimezone(MADRID).date()


def _forbidden(db: DB, p: CurrentPrincipal, message: str) -> UserFacingError:
    audit.record(db, p, "assistant.ask", "knowledge", None, result="forbidden")
    db.commit()
    return UserFacingError(status.HTTP_403_FORBIDDEN, "assistant_forbidden", message)


def _excerpt(hit: Hit) -> str:
    """Chunks start with «title[ · section]: »; the citation already carries the title."""
    cut = hit.text.find(": ", len(hit.title)) if hit.text.startswith(hit.title) else -1
    return hit.text[cut + 2:] if cut != -1 else hit.text


def _records_answer(db: DB, p: CurrentPrincipal, topic: records.Topic, cohorts: list[str]) -> AskOut:
    """KAN-195: figures come from the read-only tools (#97), never from the documents or from free SQL."""
    as_of = today()
    if len(cohorts) > 1:
        audit.record(db, p, "assistant.ask", "knowledge", None, result="no_source", mode="template", source_kind="records",
                     topic=topic, reason="cohort_required")
        db.commit()
        return AskOut(status="no_source", mode="template", retrieval=None, answer=CHOOSE_COHORT, citations=[], as_of=as_of,
                      scope_cohorts=cohorts, source_kind="records")
    found = records.answer(db, p, topic, cohorts[0])
    result = "answered" if found.has_data else "no_source"
    audit.record(db, p, "assistant.ask", "cohort", cohorts[0], result=result, mode="template", source_kind="records",
                 tool=found.tool, aggregate_only=found.aggregate_only)
    db.commit()
    return AskOut(
        status=result, mode="template", retrieval=None, answer=found.text, citations=[], as_of=as_of, scope_cohorts=cohorts,
        source_kind="records",
        record=RecordSource(tool=found.tool, source=found.source, rule=found.rule, generated_at=found.generated_at,
                            aggregate_only=found.aggregate_only),
    )


@router.post("/ask", response_model=AskOut, responses={403: {"description": "Sin documentos en tu ámbito o cohorte ajena"}},
             summary="Preguntar a la documentación del curso: respuesta citada o «no consta»")
def ask(body: AskIn, p: CurrentPrincipal, db: DB) -> AskOut:
    scope = knowledge_scope(db, p)
    if body.cohort_id is not None:
        if body.cohort_id not in scope.cohorts:
            raise _forbidden(db, p, "No tienes acceso a los documentos de esa cohorte.")
        cohort = db.get(Cohort, body.cohort_id)
        scope = KnowledgeScope(cohorts=frozenset({cohort.id}), programs=frozenset({cohort.program_id}))
    if scope.is_empty:
        raise _forbidden(db, p, "El asistente de documentación es para el equipo docente, coordinación y coders matriculados.")

    topic = records.topic_of(body.question)
    if topic is not None:
        cohorts = records.record_cohorts(db, p, topic, scope.cohorts)
        if cohorts:
            return _records_answer(db, p, topic, cohorts)

    as_of = today()
    embedder, _ = build_embedder(dry_run=False)
    try:
        result = retrieve(db, scope, body.question, today=as_of, embedder=embedder)
    finally:
        if isinstance(embedder, GeminiEmbedder):
            embedder.close()

    top = result.hits[0] if result.hits else None
    audit.record(db, p, "assistant.ask", "knowledge", None, result="answered" if top else "no_source", mode="extractive",
                 retrieval=result.mode, documents=sorted({h.source_key for h in result.hits}),
                 embedding_error=result.embedding_error)
    db.commit()
    citations = [Citation(source_key=top.source_key, title=top.title, version=top.version, valid_from=top.valid_from,
                          valid_until=top.valid_until, excerpt=_excerpt(top))] if top else []
    return AskOut(
        status="answered" if top else "no_source", mode="extractive", retrieval=result.mode,
        answer=f"Según «{top.title}» ({top.version}): {_excerpt(top)}" if top else NO_SOURCE,
        citations=citations, as_of=as_of, scope_cohorts=sorted(scope.cohorts),
    )
