"""Validate the synthetic RAG corpus and question bank (KAN-108, DA2).

Checks that the bank can be trusted before measuring the assistant with it:
  - corpus.json and questions.jsonl are valid, ids are unique and every corpus file exists;
  - every asker uses a role from ADR-0005 and a cohort that exists in the corpus;
  - each question type has the fields it needs, and referenced documents exist;
  - the expected document belongs to the asker's cohort and is current on EVAL_DATE;
  - every must_include group has at least one alternative that appears in the expected document.

Usage, from the repository root (standard library only):
    python evals/rag/validate_bank.py
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CORPUS_DIR = ROOT / "corpus"
# Fixed reference date, so the bank does not expire with the calendar.
EVAL_DATE = date(2026, 12, 1)
ROLES = {"admin", "docente", "coordinacion", "captacion", "seleccion", "coder"}  # coder arrives with F3
ANSWERED = {"answerable", "obsolete_trap"}
ABSTAIN = {"unanswerable", "other_cohort", "restricted", "prompt_injection"}


def is_current(doc: dict) -> bool:
    valid_from = date.fromisoformat(doc["valid_from"])
    valid_until = date.fromisoformat(doc["valid_until"]) if doc.get("valid_until") else None
    return doc["status"] == "vigente" and valid_from <= EVAL_DATE and (valid_until is None or EVAL_DATE <= valid_until)


def main() -> int:
    errors: list[str] = []
    corpus = json.loads((CORPUS_DIR / "corpus.json").read_text(encoding="utf-8"))
    docs = {d["id"]: d for d in corpus}
    if len(docs) != len(corpus):
        errors.append("corpus.json: duplicated document ids")
    texts = {}
    for doc_id, doc in docs.items():
        path = CORPUS_DIR / doc["file"]
        if not path.is_file():
            errors.append(f"{doc_id}: missing file {doc['file']}")
            continue
        texts[doc_id] = path.read_text(encoding="utf-8").lower()
        if not doc.get("synthetic"):
            errors.append(f"{doc_id}: must be marked as synthetic")
    cohorts = {d["cohort"] for d in corpus}

    questions = []
    for n, line in enumerate((ROOT / "questions.jsonl").read_text(encoding="utf-8").splitlines(), start=1):
        if line.strip():
            try:
                questions.append(json.loads(line))
            except json.JSONDecodeError as exc:
                errors.append(f"questions.jsonl line {n}: invalid JSON ({exc.msg})")

    ids = [q.get("id") for q in questions]
    for dup in [i for i, c in Counter(ids).items() if c > 1]:
        errors.append(f"{dup}: duplicated question id")

    for q in questions:
        qid, qtype = q.get("id"), q.get("type")
        asker = q.get("asker", {})
        if asker.get("role") not in ROLES:
            errors.append(f"{qid}: unknown role {asker.get('role')!r}")
        if asker.get("cohort") not in cohorts:
            errors.append(f"{qid}: unknown cohort {asker.get('cohort')!r}")
        for doc_id in q.get("forbidden_docs", []):
            if doc_id not in docs:
                errors.append(f"{qid}: forbidden doc {doc_id} not in corpus")
        expected = q.get("expected_doc")
        if qtype in ANSWERED:
            doc = docs.get(expected)
            if doc is None:
                errors.append(f"{qid}: expected_doc {expected!r} not in corpus")
                continue
            if doc["cohort"] != asker.get("cohort"):
                errors.append(f"{qid}: expected_doc belongs to another cohort")
            if not is_current(doc):
                errors.append(f"{qid}: expected_doc is not current on {EVAL_DATE}")
            if expected in q.get("forbidden_docs", []):
                errors.append(f"{qid}: expected_doc is also forbidden")
            groups = q.get("must_include")
            if not groups or not all(isinstance(g, list) and g for g in groups):
                errors.append(f"{qid}: must_include needs a list of non-empty alternative lists")
                continue
            for group in groups:
                if not any(alt.lower() in texts.get(expected, "") for alt in group):
                    errors.append(f"{qid}: no alternative of {group} appears in {expected}")
        elif qtype in ABSTAIN:
            if expected is not None or q.get("expected_answer") is not None or q.get("must_include"):
                errors.append(f"{qid}: abstention questions need null expected_doc/answer and empty must_include")
        else:
            errors.append(f"{qid}: unknown type {qtype!r}")

    for doc_id, doc in docs.items():
        if doc["status"] == "obsoleto" and is_current(doc):
            errors.append(f"{doc_id}: marked obsolete but would be current on {EVAL_DATE}")

    split = Counter(q.get("type") for q in questions)
    print(f"Corpus: {len(docs)} documents · Questions: {len(questions)} · Reference date: {EVAL_DATE}")
    print("Split: " + ", ".join(f"{t} {c}" for t, c in sorted(split.items())))
    for error in errors:
        print(f"[FAIL] {error}")
    print("Result: " + ("ALL PASSED" if not errors else f"{len(errors)} FAILED"))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
