"""KAN-130: the corpus loader accepts only complete, synthetic, in-folder documents with a known scope and owner."""

import json
from datetime import date

import pytest

from app.core.config import settings
from app.modules.knowledge.corpus import COHORT_SCOPE, CorpusError, load_corpus
from app.seed import load_seed

VALID = {
    "id": "T1", "file": "t1.md", "title": "Documento sintético", "cohort": "A", "version": "v1",
    "valid_from": "2026-11-01", "valid_until": "2026-12-22", "status": "vigente", "synthetic": True, "maintained_by": "docente",
}


def make_corpus(folder, *entries, files=None):
    for name, text in (files or {"t1.md": "# Documento\n\nTexto sintético.\n"}).items():
        (folder / name).write_text(text, encoding="utf-8")
    (folder / "corpus.json").write_text(json.dumps(list(entries)), encoding="utf-8")
    return folder


def test_real_corpus_loads_every_document_with_its_real_cohort():
    documents, rejected = load_corpus(settings.corpus_path)
    assert rejected == []
    assert {d.source_key: d.scope_id for d in documents} == {
        "A1": "COH-IA", "A2": "COH-IA", "A3": "COH-IA", "A4": "COH-IA", "A5": "COH-IA", "B1": "COH-DATA",
    }
    assert all(d.scope_type == "cohort" and d.is_synthetic and d.text.strip() for d in documents)


def test_every_mapped_cohort_exists_in_the_synthetic_seed():
    # Alarm: if the seed cohort IDs change (KAN-136), this fails before the RAG filters by a cohort that does not exist.
    seed_cohorts = {c["id"] for c in load_seed()["cohortes"]}
    assert set(COHORT_SCOPE.values()) <= seed_cohorts


def test_a_valid_entry_becomes_a_source_document(tmp_path):
    [document], rejected = load_corpus(make_corpus(tmp_path, VALID))
    assert rejected == []
    assert (document.scope_type, document.scope_id, document.valid_from, document.valid_until, document.maintained_by) == (
        "cohort", "COH-IA", date(2026, 11, 1), date(2026, 12, 22), "docente",
    )


def test_valid_until_is_optional(tmp_path):
    entry = {k: v for k, v in VALID.items() if k != "valid_until"}
    [document], _ = load_corpus(make_corpus(tmp_path, entry))
    assert document.valid_until is None


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"maintained_by": None}, "missing fields: maintained_by"),  # CA12
        ({"cohort": "Z"}, "has no scope mapping"),  # CA8
        ({"synthetic": False}, "only synthetic documents"),
        ({"maintained_by": "Persona Sintética"}, "must be a staff role"),  # a role, never a person's name
        ({"status": "borrador"}, "status must be one of"),
        ({"valid_from": "19/11/2026"}, "not an ISO date"),
        ({"valid_until": "2026-10-01"}, "before valid_from"),
        ({"version": "v" * 21}, "longer than 20"),
        ({"file": "../outside.md"}, "inside the corpus folder"),
        ({"file": "missing.md"}, "file not found"),
    ],
)
def test_invalid_entries_are_rejected_with_a_reason(tmp_path, changes, reason):
    documents, rejected = load_corpus(make_corpus(tmp_path, {**VALID, **changes}))
    assert documents == []
    [entry] = rejected
    assert entry.source_key == "T1" and reason in entry.reason


def test_an_empty_document_is_rejected(tmp_path):
    documents, rejected = load_corpus(make_corpus(tmp_path, VALID, files={"t1.md": "  \n"}))
    assert documents == [] and "empty" in rejected[0].reason


def test_one_bad_entry_does_not_block_the_others(tmp_path):
    documents, rejected = load_corpus(make_corpus(tmp_path, VALID, {**VALID, "id": "T2", "cohort": "Z"}))
    assert [d.source_key for d in documents] == ["T1"]
    assert [r.source_key for r in rejected] == ["T2"]


@pytest.mark.parametrize(
    ("manifest", "message"),
    [
        (None, "not found"),
        ("{not json", "not valid JSON"),
        ('{"id": "T1"}', "must be a list"),
        (json.dumps([VALID, VALID]), "duplicated document ids: T1"),
    ],
)
def test_a_broken_manifest_stops_the_whole_ingest(tmp_path, manifest, message):
    if manifest is not None:
        (tmp_path / "corpus.json").write_text(manifest, encoding="utf-8")
    with pytest.raises(CorpusError, match=message):
        load_corpus(tmp_path)
