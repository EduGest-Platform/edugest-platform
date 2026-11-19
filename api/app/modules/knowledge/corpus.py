"""Loads the synthetic course corpus for the RAG knowledge ingest (KAN-130).

This is the only module that knows documents come from a folder (corpus.json plus one Markdown file each).
The pipeline receives SourceDocument objects, so a future upload endpoint can reuse it unchanged.
Error messages name the entry and the field, never the document content.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from app.core.authz import ROLE_PERMISSIONS

MANIFEST = "corpus.json"
# Corpus cohorts (the letters used by the question bank) -> real cohort IDs of the synthetic seed.
COHORT_SCOPE = {"A": "COH-IA", "B": "COH-DATA"}
STATUSES = ("vigente", "obsoleto")
# The responsible area is a staff role, never a person's name (no personal data in the knowledge base).
MAINTAINER_ROLES = frozenset(ROLE_PERMISSIONS)
REQUIRED_FIELDS = ("id", "file", "title", "cohort", "version", "valid_from", "status", "synthetic", "maintained_by")
# Same limits as the knowledge_document columns.
MAX_LENGTH = {"id": 100, "title": 200, "version": 20}


class CorpusError(ValueError):
    """The corpus, or one of its entries, cannot be loaded."""


@dataclass(frozen=True)
class SourceDocument:
    """One course document ready for the pipeline, whatever its origin."""

    source_key: str
    title: str
    version: str
    scope_type: str
    scope_id: str
    valid_from: date
    valid_until: date | None
    status: str
    maintained_by: str
    is_synthetic: bool
    text: str


@dataclass(frozen=True)
class RejectedEntry:
    source_key: str
    reason: str


def load_corpus(corpus_dir: str | Path) -> tuple[list[SourceDocument], list[RejectedEntry]]:
    """Returns the valid documents and the rejected entries. A broken manifest stops everything."""
    root = Path(corpus_dir).resolve()
    documents: list[SourceDocument] = []
    rejected: list[RejectedEntry] = []
    for entry in _read_manifest(root / MANIFEST):
        try:
            documents.append(_to_document(root, entry))
        except CorpusError as exc:
            rejected.append(RejectedEntry(str(entry.get("id") or "?"), str(exc)))
    return documents, rejected


def _read_manifest(path: Path) -> list[dict]:
    if not path.is_file():
        raise CorpusError(f"{MANIFEST} not found in the corpus folder")
    try:
        entries = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise CorpusError(f"{MANIFEST} is not valid JSON (line {exc.lineno})") from exc
    if not isinstance(entries, list) or not all(isinstance(e, dict) for e in entries):
        raise CorpusError(f"{MANIFEST} must be a list of objects")
    ids = [e.get("id") for e in entries]
    duplicated = sorted({str(i) for i in ids if ids.count(i) > 1})
    if duplicated:
        raise CorpusError(f"duplicated document ids: {', '.join(duplicated)}")
    return entries


def _to_document(root: Path, entry: dict) -> SourceDocument:
    missing = [field for field in REQUIRED_FIELDS if entry.get(field) in (None, "")]
    if missing:
        raise CorpusError(f"missing fields: {', '.join(missing)}")
    if entry["synthetic"] is not True:
        raise CorpusError("only synthetic documents can be ingested")
    if entry["cohort"] not in COHORT_SCOPE:
        raise CorpusError(f"cohort {entry['cohort']!r} has no scope mapping")
    if entry["status"] not in STATUSES:
        raise CorpusError(f"status must be one of {', '.join(STATUSES)}")
    if entry["maintained_by"] not in MAINTAINER_ROLES:
        raise CorpusError(f"maintained_by must be a staff role: {', '.join(sorted(MAINTAINER_ROLES))}")
    for field, limit in MAX_LENGTH.items():
        if len(str(entry[field])) > limit:
            raise CorpusError(f"{field} is longer than {limit} characters")
    valid_from = _iso_date(entry, "valid_from")
    valid_until = _iso_date(entry, "valid_until") if entry.get("valid_until") else None
    if valid_until and valid_until < valid_from:
        raise CorpusError("valid_until is before valid_from")
    return SourceDocument(
        source_key=str(entry["id"]),
        title=str(entry["title"]),
        version=str(entry["version"]),
        scope_type="cohort",
        scope_id=COHORT_SCOPE[entry["cohort"]],
        valid_from=valid_from,
        valid_until=valid_until,
        status=entry["status"],
        maintained_by=entry["maintained_by"],
        is_synthetic=True,
        text=_read_text(root, str(entry["file"])),
    )


def _iso_date(entry: dict, field: str) -> date:
    try:
        return date.fromisoformat(str(entry[field]))
    except ValueError as exc:
        raise CorpusError(f"{field} is not an ISO date (YYYY-MM-DD)") from exc


def _read_text(root: Path, name: str) -> str:
    path = (root / name).resolve()
    if root not in path.parents:
        raise CorpusError("file must be inside the corpus folder")
    if not path.is_file():
        raise CorpusError("file not found")
    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise CorpusError("document is empty")
    return text
