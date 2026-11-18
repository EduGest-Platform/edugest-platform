"""Smoke test for ADR-0005 (KAN-113).

Checks that the pieces chosen in the ADR fit together, using the synthetic corpus of the
question bank (evals/rag/corpus, KAN-108):
  1. Gemini Embedding turns each corpus document into a normalised 768-dimension vector.
  2. PostgreSQL + pgvector stores them and finds the closest one (cosine distance, exact search).
  3. The cohort filter and the freshness filter are applied in the same query, so no document
     from another cohort and no obsolete document is ever returned.
  4. Negative control: the same query WITHOUT filters does return the forbidden document,
     which proves that the filter, and not luck, is what keeps it out.
  5. PostgreSQL keyword search (Spanish) works as a fallback.

Everything runs in a TEMPORARY table of the local test database (gistar_test), so nothing is
left behind. Freshness uses a fixed reference date, so the test does not expire.

Requirements: the Docker database running and the API dev extra installed
(`pip install -e "api[dev]"`, which provides httpx and psycopg). The database user must be
allowed to run CREATE EXTENSION (the Compose user is).

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

# (question id in questions.jsonl, asker cohort, expected document or None, forbidden document)
CASES = [
    ("q01", "A", "A1", "B1"),  # answerable: project deadline
    ("q05", "A", "A2", "A3"),  # answerable: current calendar, never the obsolete one
    ("q19", "A", None, "B1"),  # other cohort: cohort B's project must not leak to A
    ("q02", "B", None, "A1"),  # other cohort, opposite direction
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
            print(f"Indexed {len(corpus)} synthetic documents with {EMBED_MODEL} ({EMBED_DIM} dims, normalised).")
            print(f"Reference date for freshness: {EVAL_DATE}\n")

            # Scope and freshness go in the WHERE clause of the same query as the ranking.
            scope_sql = (
                "cohort = %s AND status = 'vigente' AND valid_from <= %s "
                "AND (valid_until IS NULL OR valid_until >= %s)"
            )
            for qid, cohort, expected, forbidden in CASES:
                question = questions[qid]["question"]
                qvec = as_vector(embed(client, question, "RETRIEVAL_QUERY"))
                rows = conn.execute(
                    f"""
                    SELECT doc_id, 1 - (embedding <=> %s::vector) AS similarity FROM smoke_chunk
                    WHERE {scope_sql} ORDER BY embedding <=> %s::vector LIMIT 3
                    """,
                    (qvec, cohort, EVAL_DATE, EVAL_DATE, qvec),
                ).fetchall()
                control = conn.execute(
                    "SELECT doc_id FROM smoke_chunk ORDER BY embedding <=> %s::vector LIMIT 3", (qvec,)
                ).fetchall()
                returned = [r[0] for r in rows]
                ok_filter = forbidden not in returned
                ok_control = forbidden in [r[0] for r in control]
                ok_expected = expected is None or (returned[:1] == [expected])
                ok = ok_filter and ok_control and ok_expected
                failures += 0 if ok else 1
                print(f"[{'PASS' if ok else 'FAIL'}] {qid} (cohort {cohort}): {question}")
                for doc_id, similarity in rows:
                    print(f"       {similarity:.3f}  {doc_id}")
                print(f"       filter keeps {forbidden} out: {'yes' if ok_filter else 'NO'}")
                print(f"       negative control, without filters {forbidden} is in the top 3: "
                      f"{'yes' if ok_control else 'NO (control too weak)'}")
                if expected is None:
                    top = f"{rows[0][1]:.3f}" if rows else "none"
                    print(f"       [INFO] no expected document; best allowed similarity {top}. "
                          "Abstention is measured with the threshold in DA6, not here.")
                print()

            rows = conn.execute(
                f"""
                SELECT doc_id FROM smoke_chunk
                WHERE {scope_sql} AND to_tsvector('spanish', body) @@ plainto_tsquery('spanish', %s)
                ORDER BY doc_id
                """,
                (KEYWORD_COHORT, EVAL_DATE, EVAL_DATE, KEYWORD_QUERY),
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
