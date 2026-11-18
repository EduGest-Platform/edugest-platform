"""Smoke test for ADR-0005 (KAN-113).

Checks that the pieces chosen in the ADR fit together, using the synthetic corpus of the
question bank (evals/rag/corpus, KAN-108). It has two separate parts:

Access control (deterministic, no ranking involved):
  Each restriction (cohort, status, validity dates) is checked on its own. For every case the
  forbidden document must be eligible when only that restriction is removed, and must be
  excluded when the full filter is applied. Two synthetic variants are added for this:
  an expired document still marked current, and an obsolete document with current dates.

Retrieval quality (depends on Gemini Embedding):
  The filtered semantic search returns the expected document first, and PostgreSQL keyword
  search (Spanish) works as a fallback.

Everything runs in a TEMPORARY table, and freshness uses a fixed reference date, so the test
does not expire. CREATE EXTENSION vector, however, is a persistent change to the database, so
the script refuses to run unless the database name ends in "_test" (the Compose test database
is gistar_test). The database user must be allowed to create extensions (the Compose user is).

Requirements: the Docker database running and the API dev extra installed
(`pip install -e "api[dev]"`, which provides httpx and psycopg).

Usage, from the repository root (Linux, macOS or Windows):
    python evals/rag/smoke_adr0005.py
GISTAR_TEST_DATABASE_URL and GEMINI_API_KEY are read from the environment or, if missing,
from api/.env. Their values are never printed.
"""

from __future__ import annotations

import json
import math
import os
import sys
import time
from datetime import date
from pathlib import Path

import httpx
import psycopg

REPO = Path(__file__).resolve().parents[2]
CORPUS_DIR = REPO / "evals" / "rag" / "corpus"
EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 768
EMBED_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{EMBED_MODEL}:embedContent"
EVAL_DATE = date(2026, 12, 1)  # same reference date as evals/rag/validate_bank.py
RETRY_STATUS = {429, 500, 503}

# Filter parts. Each one can be removed on its own to prove that it is the one doing the work.
FILTERS = {
    "cohort": "cohort = %(cohort)s",
    "status": "status = 'vigente'",
    "dates": "valid_from <= %(eval_date)s AND (valid_until IS NULL OR valid_until >= %(eval_date)s)",
}

# Synthetic variants of A2, only in the temporary table: each breaks exactly one freshness rule.
VARIANTS = [
    ("X-EXPIRED", "vigente", date(2026, 9, 1), date(2026, 11, 15)),   # current status, expired dates
    ("X-OBSOLETE", "obsoleto", date(2026, 11, 1), date(2026, 12, 22)),  # obsolete status, current dates
]

# (description, asker cohort, forbidden document, restriction that must exclude it)
ACCESS_CASES = [
    ("cohort B document never reaches cohort A", "A", "B1", "cohort"),
    ("cohort A document never reaches cohort B", "B", "A1", "cohort"),
    ("obsolete document with current dates is excluded", "A", "X-OBSOLETE", "status"),
    ("expired document still marked current is excluded", "A", "X-EXPIRED", "dates"),
]

# (question id in questions.jsonl, asker cohort, expected first document or None)
RETRIEVAL_CASES = [
    ("q01", "A", "A1"),  # project deadline
    ("q05", "A", "A2"),  # current calendar, never the obsolete one
    ("q19", "A", None),  # other cohort's project: information only
    ("q02", "B", None),  # other cohort, opposite direction: information only
]
KEYWORD_QUERY, KEYWORD_COHORT, KEYWORD_EXPECTED = "clases presenciales", "A", ["A2"]


def read_settings() -> dict[str, str]:
    wanted = ("GISTAR_TEST_DATABASE_URL", "GEMINI_API_KEY")
    values = {k: os.environ.get(k, "") for k in wanted}
    env_file = REPO / "api" / ".env"
    if not all(values.values()) and env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            key = key.strip()
            if sep and key in wanted and not values[key]:
                values[key] = value.strip().strip('"').strip("'")
    return values


def embed(client: httpx.Client, text: str, task: str) -> list[float]:
    body = {
        "model": f"models/{EMBED_MODEL}",
        "content": {"parts": [{"text": text}]},
        "taskType": task,
        "outputDimensionality": EMBED_DIM,
    }
    for attempt in range(3):
        response = client.post(EMBED_URL, json=body)
        if response.status_code not in RETRY_STATUS:
            break
        time.sleep(2 * (attempt + 1))
    if response.status_code != 200:
        raise RuntimeError(f"Gemini embedding API answered HTTP {response.status_code}")
    values = response.json()["embedding"]["values"]
    if len(values) != EMBED_DIM:
        raise RuntimeError(f"Expected {EMBED_DIM} dimensions, got {len(values)}")
    norm = math.sqrt(sum(v * v for v in values))  # vectors below 3072 dimensions are not normalised
    return [v / norm for v in values]


def as_vector(values: list[float]) -> str:
    return "[" + ",".join(f"{v:.7f}" for v in values) + "]"


def where(parts: list[str]) -> str:
    return " AND ".join(FILTERS[p] for p in parts) or "TRUE"


def eligible(conn: psycopg.Connection, parts: list[str], cohort: str) -> set[str]:
    rows = conn.execute(
        f"SELECT doc_id FROM smoke_chunk WHERE {where(parts)}",
        {"cohort": cohort, "eval_date": EVAL_DATE},
    ).fetchall()
    return {r[0] for r in rows}


def main() -> int:
    settings = read_settings()
    if not all(settings.values()):
        print("Missing GISTAR_TEST_DATABASE_URL or GEMINI_API_KEY (environment or api/.env).")
        return 2
    db_url = settings["GISTAR_TEST_DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://", 1)
    corpus = json.loads((CORPUS_DIR / "corpus.json").read_text(encoding="utf-8"))
    questions = {}
    for line in (REPO / "evals" / "rag" / "questions.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            q = json.loads(line)
            questions[q["id"]] = q

    failures = 0
    try:
        with httpx.Client(timeout=30, headers={"x-goog-api-key": settings["GEMINI_API_KEY"]}) as client, \
                psycopg.connect(db_url) as conn:
            if not conn.info.dbname.endswith("_test"):
                print("Refusing to run: the database name must end in '_test' (CREATE EXTENSION is persistent).")
                return 2
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.execute(
                f"""
                CREATE TEMP TABLE smoke_chunk (
                    doc_id text, cohort text, title text, version text, valid_from date,
                    valid_until date, status text, body text, embedding_model text,
                    embedding vector({EMBED_DIM})
                ) ON COMMIT DROP
                """
            )
            for doc in corpus:
                body = (CORPUS_DIR / doc["file"]).read_text(encoding="utf-8")
                vector = as_vector(embed(client, body, "RETRIEVAL_DOCUMENT"))
                conn.execute(
                    "INSERT INTO smoke_chunk VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::vector)",
                    (doc["id"], doc["cohort"], doc["title"], doc["version"], doc["valid_from"],
                     doc["valid_until"], doc["status"], body, EMBED_MODEL, vector),
                )
            for doc_id, status, valid_from, valid_until in VARIANTS:
                conn.execute(
                    """
                    INSERT INTO smoke_chunk
                    SELECT %s, cohort, title, 'variant', %s, %s, %s, body, embedding_model, embedding
                    FROM smoke_chunk WHERE doc_id = 'A2'
                    """,
                    (doc_id, valid_from, valid_until, status),
                )
            print(f"Indexed {len(corpus)} synthetic documents with {EMBED_MODEL} ({EMBED_DIM} dims, normalised)")
            print(f"plus {len(VARIANTS)} freshness variants. Reference date: {EVAL_DATE}\n")

            print("Access control (deterministic)")
            all_parts = list(FILTERS)
            for description, cohort, forbidden, restriction in ACCESS_CASES:
                relaxed = [p for p in all_parts if p != restriction]
                without = forbidden in eligible(conn, relaxed, cohort)
                with_filter = forbidden in eligible(conn, all_parts, cohort)
                ok = without and not with_filter
                failures += 0 if ok else 1
                print(f"[{'PASS' if ok else 'FAIL'}] {description}")
                print(f"       without the {restriction} filter {forbidden} is eligible: {'yes' if without else 'NO'}; "
                      f"with the full filter it is excluded: {'yes' if not with_filter else 'NO'}")
            print()

            print("Retrieval quality (Gemini Embedding)")
            scope = where(all_parts)
            for qid, cohort, expected in RETRIEVAL_CASES:
                question = questions[qid]["question"]
                qvec = as_vector(embed(client, question, "RETRIEVAL_QUERY"))
                rows = conn.execute(
                    f"""
                    SELECT doc_id, 1 - (embedding <=> %(q)s::vector) AS similarity FROM smoke_chunk
                    WHERE {scope} ORDER BY embedding <=> %(q)s::vector LIMIT 3
                    """,
                    {"q": qvec, "cohort": cohort, "eval_date": EVAL_DATE},
                ).fetchall()
                ranking = "  ".join(f"{doc_id} {similarity:.3f}" for doc_id, similarity in rows)
                if expected is None:
                    print(f"[INFO] {qid} (cohort {cohort}): {question}")
                    print(f"       {ranking}  (no expected document; abstention is measured in DA6)")
                    continue
                ok = bool(rows) and rows[0][0] == expected
                failures += 0 if ok else 1
                print(f"[{'PASS' if ok else 'FAIL'}] {qid} (cohort {cohort}): {question}")
                print(f"       {ranking}  (expected first: {expected})")

            rows = conn.execute(
                f"""
                SELECT doc_id FROM smoke_chunk
                WHERE {scope} AND to_tsvector('spanish', body) @@ plainto_tsquery('spanish', %(text)s)
                ORDER BY doc_id
                """,
                {"cohort": KEYWORD_COHORT, "eval_date": EVAL_DATE, "text": KEYWORD_QUERY},
            ).fetchall()
            found = [r[0] for r in rows]
            keyword_ok = found == KEYWORD_EXPECTED
            failures += 0 if keyword_ok else 1
            print(f"[{'PASS' if keyword_ok else 'FAIL'}] Keyword fallback '{KEYWORD_QUERY}' -> {found}")
    except (RuntimeError, httpx.HTTPError, psycopg.Error) as exc:
        print(f"Could not run the smoke test: {type(exc).__name__}: {exc}")
        return 2

    print(f"\nResult: {'ALL PASSED' if failures == 0 else f'{failures} FAILED'}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
