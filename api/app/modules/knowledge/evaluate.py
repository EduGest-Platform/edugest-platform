"""Measures retrieval on the question bank (groundwork for KAN-188). Synthetic data only, no AI provider needed.

Usage, from api/, ALWAYS against a disposable database (for example the test one), because it runs the ingest:
    GISTAR_DATABASE_URL=<test database> python -m app.modules.knowledge.evaluate            # table + summary
    GISTAR_DATABASE_URL=<test database> python -m app.modules.knowledge.evaluate --sweep    # summary per threshold

Each question is asked with the scope of its asker's cohort. A question with an expected document is right when that
document is the first hit; one without (unanswerable, other cohort, restricted, injection) is right when it abstains.
Caution: tuning the threshold on this same bank can overfit it; KAN-188 should add questions the tuning never saw.
"""

import argparse
import json
from datetime import date
from pathlib import Path

from app.core.config import settings
from app.core.db import SessionLocal
from app.modules.knowledge import retrieval
from app.modules.knowledge.corpus import COHORT_SCOPE
from app.modules.knowledge.ingest import run_ingest
from app.modules.knowledge.scope import KnowledgeScope

REFERENCE_DATE = date(2026, 12, 1)  # the bank's reference date (evals/rag/validate_bank.py)
PROGRAM = {"A": "P-IA", "B": "P-DATA"}


def load(corpus_dir: str) -> tuple[list[dict], dict[str, dict]]:
    root = Path(corpus_dir)
    bank = [json.loads(line) for line in (root.parent / "questions.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    manifest = {e["id"]: e for e in json.loads((root / "corpus.json").read_text(encoding="utf-8"))}
    return bank, manifest


def scope_for(letter: str) -> KnowledgeScope:
    return KnowledgeScope(cohorts=frozenset({COHORT_SCOPE[letter]}), programs=frozenset({PROGRAM[letter]}))


def evaluate(db, bank: list[dict], manifest: dict[str, dict]) -> list[dict]:
    rows = []
    for q in bank:
        letter = q["asker"]["cohort"]
        result = retrieval.retrieve(db, scope_for(letter), q["question"], today=REFERENCE_DATE)
        found = [hit.source_key for hit in result.hits]
        expected = q["expected_doc"]
        rows.append({
            "id": q["id"], "type": q["type"], "expected": expected or "-", "found": found,
            "coverage": result.hits[0].coverage if result.hits else None,
            "right": (bool(found) and found[0] == expected) if expected else not found,
            "recall3": (expected in found) if expected else None,
            "leak": any(manifest[key]["cohort"] != letter for key in found),
            "obsolete": any(manifest[key]["status"] != "vigente" for key in found),
        })
    return rows


def summary(rows: list[dict]) -> str:
    answerable = [r for r in rows if r["expected"] != "-"]
    abstain = [r for r in rows if r["expected"] == "-"]
    return (f"right {sum(r['right'] for r in rows)}/{len(rows)} · "
            f"top-1 {sum(r['right'] for r in answerable)}/{len(answerable)} · "
            f"recall@3 {sum(r['recall3'] for r in answerable)}/{len(answerable)} · "
            f"correct abstention {sum(r['right'] for r in abstain)}/{len(abstain)} · "
            f"leaks {sum(r['leak'] for r in rows)} · obsolete {sum(r['obsolete'] for r in rows)}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Measure RAG retrieval on the synthetic question bank.")
    parser.add_argument("--sweep", action="store_true", help="print the summary for several coverage thresholds")
    args = parser.parse_args(argv)
    bank, manifest = load(settings.corpus_path)
    with SessionLocal() as db:
        run_ingest(db, settings.corpus_path)
        if args.sweep:
            for threshold in (0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8):
                retrieval.MIN_COVERAGE = threshold
                print(f"MIN_COVERAGE={threshold:.1f} · {summary(evaluate(db, bank, manifest))}")
            return 0
        rows = evaluate(db, bank, manifest)
    for r in rows:
        coverage = "-" if r["coverage"] is None else f"{r['coverage']:.2f}"
        print(f"{r['id']:<4} {r['type']:<17} expected {r['expected']:<3} found {','.join(r['found']) or '-':<12} "
              f"coverage {coverage:<5} {'OK' if r['right'] else 'FALLO'}{' FUGA' if r['leak'] else ''}{' OBSOLETO' if r['obsolete'] else ''}")
    print(summary(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
