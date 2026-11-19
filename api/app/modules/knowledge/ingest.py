"""Command line entry point of the RAG knowledge ingest (KAN-130).

Usage, from api/:  python -m app.modules.knowledge.ingest [--dry-run] [--corpus PATH]
Repeatable: unchanged documents are skipped by content hash. Prints one line per document and a summary.
Exit code: 0 all ingested or unchanged · 1 some document rejected or failed · 2 corpus or database unusable.
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import SessionLocal, utcnow
from app.modules.identity.models import Person
from app.modules.knowledge.corpus import CorpusError, load_corpus
from app.modules.knowledge.pipeline import IngestResult, ingest_document, retire_missing

ACTION_LABEL = {
    "created": "nuevo", "updated": "actualizado", "unchanged": "sin cambios",
    "rejected": "rechazado", "retired": "retirado", "failed": "error",
}
TITLE_WIDTH = 30


def run_ingest(db: Session, corpus_dir: str, dry_run: bool = False) -> list[IngestResult]:
    """One transaction per document. A dry run does the same work and rolls every transaction back."""
    documents, unreadable = load_corpus(corpus_dir)
    known_names = list(db.scalars(select(Person.display_name)))
    results = [IngestResult(entry.source_key, "-", "rejected", reason=entry.reason) for entry in unreadable]
    for doc in documents:
        try:
            result = ingest_document(db, doc, known_names)
            _finish(db, dry_run)
        except SQLAlchemyError as exc:
            db.rollback()
            result = IngestResult(doc.source_key, doc.version, "failed", title=doc.title, reason=_safe_error(exc))
        results.append(result)
    results += retire_missing(db, {d.source_key: d.version for d in documents}, {e.source_key for e in unreadable})
    _finish(db, dry_run)
    return results


def format_report(results: list[IngestResult], corpus_dir: str, dry_run: bool) -> str:
    mode = " · simulación: no se guarda nada" if dry_run else ""
    header = (
        f"{'ID':<6}{'Título':<{TITLE_WIDTH + 2}}{'Versión':<9}{'Cohorte':<10}{'Estado':<10}"
        f"{'Vigencia':<27}{'Acción':<13}{'Frag.':<7}{'Vector':<8}Responsable"
    )
    lines = [f"Ingesta RAG · {utcnow():%Y-%m-%d %H:%M} UTC · corpus: {corpus_dir}{mode}", header]
    for r in results:
        validity = f"{r.valid_from} → {r.valid_until or 'sin fin'}" if r.valid_from else "-"
        lines.append(
            f"{r.source_key:<6}{_short(r.title):<{TITLE_WIDTH + 2}}{r.version:<9}{(r.scope_id or '-'):<10}{(r.status or '-'):<10}"
            f"{validity:<27}{ACTION_LABEL[r.action]:<13}{_count(r.chunks):<7}{_vector(r):<8}{r.maintained_by or '-'}"
        )
    counts = Counter(r.action for r in results)
    summary = " · ".join(f"{counts[action]} {label}" for action, label in ACTION_LABEL.items() if counts[action])
    lines.append(f"Resumen: {len(results)} documentos · {summary or 'nada que hacer'}")
    lines += [f"  {r.source_key}: {r.reason}" for r in results if r.reason]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest the synthetic course corpus into the RAG knowledge base (KAN-130).")
    parser.add_argument("--corpus", default=settings.corpus_path, help="folder with corpus.json and the Markdown documents")
    parser.add_argument("--dry-run", action="store_true", help="validate and report without saving anything")
    args = parser.parse_args(argv)
    try:
        with SessionLocal() as db:
            results = run_ingest(db, args.corpus, dry_run=args.dry_run)
    except CorpusError as exc:
        print(f"Ingesta RAG: el corpus no se puede usar: {exc}", file=sys.stderr)
        return 2
    except SQLAlchemyError as exc:
        print(f"Ingesta RAG: la base de datos no está disponible ({type(exc).__name__})", file=sys.stderr)
        return 2
    print(format_report(results, args.corpus, args.dry_run))
    return 1 if any(r.action in ("rejected", "failed") for r in results) else 0


def _finish(db: Session, dry_run: bool) -> None:
    if dry_run:
        db.rollback()
    else:
        db.commit()


def _short(title: str | None) -> str:
    if not title:
        return "-"
    return title if len(title) <= TITLE_WIDTH else title[: TITLE_WIDTH - 1] + "…"


def _count(chunks: int | None) -> str:
    return "-" if chunks is None else str(chunks)


def _vector(result: IngestResult) -> str:
    if result.chunks is None:
        return "-"
    return "sí" if result.embedded else "no"


def _safe_error(exc: SQLAlchemyError) -> str:
    """Error class plus the constraint or column involved. Never the message: it can echo row values."""
    diag = getattr(getattr(exc, "orig", None), "diag", None)
    detail = getattr(diag, "constraint_name", None) or getattr(diag, "column_name", None)
    return f"{type(exc).__name__} ({detail})" if detail else type(exc).__name__


if __name__ == "__main__":
    sys.exit(main())
