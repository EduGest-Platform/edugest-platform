"""Smoke test for ADR-0005 (KAN-113).

Checks that the pieces chosen in the ADR fit together:
  1. Gemini Embedding turns synthetic documents into 768-dimension vectors.
  2. PostgreSQL + pgvector stores them and finds the closest one.
  3. The cohort filter and the freshness filter are applied BEFORE searching:
     no document from another cohort and no expired document is ever returned.
  4. PostgreSQL keyword search (Spanish) works as a fallback.

Everything runs in a TEMPORARY table of the local test database (gistar_test),
so nothing is left behind. Synthetic data only.

Usage, from the repository root:
    export $(grep -E '^(GISTAR_TEST_DATABASE_URL|GEMINI_API_KEY)=' api/.env | xargs)
    python evals/rag/smoke_adr0005.py
"""

from __future__ import annotations

import os
import sys
from datetime import date

import httpx
import psycopg

EMBED_MODEL = "gemini-embedding-001"
EMBED_DIM = 768
EMBED_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{EMBED_MODEL}:embedContent"
)
USER_COHORT = "ia-2026-a"

# Synthetic documents: (id, cohort, title, version, valid_until, status, text)
DOCUMENTS = [
    (
        "brief-rag",
        "ia-2026-a",
        "Brief del proyecto RAG corporativo",
        "v2",
        date(2026, 12, 31),
        "vigente",
        "La entrega final del proyecto RAG corporativo es el viernes 12 de "
        "diciembre a las 15:00. Se entrega por GitHub con un README y una demo.",
    ),
    (
        "calendario-v2",
        "ia-2026-a",
        "Calendario de la cohorte",
        "v2",
        date(2026, 12, 31),
        "vigente",
        "Las clases presenciales son los lunes y los martes de 9:00 a 14:30 en "
        "el aula 2. De miércoles a viernes las clases son en remoto.",
    ),
    (
        "calendario-v1",
        "ia-2026-a",
        "Calendario de la cohorte (antiguo)",
        "v1",
        date(2026, 10, 31),
        "obsoleto",
        "Las clases presenciales son los jueves de 9:00 a 14:30 en el aula 5.",
    ),
    (
        "brief-vision",
        "ia-2026-b",
        "Brief del proyecto de visión por computador",
        "v1",
        date(2026, 12, 31),
        "vigente",
        "La entrega del proyecto de visión por computador es el viernes 5 de "
        "diciembre. Se entrega un cuaderno con el modelo entrenado.",
    ),
]

# (question, expected document id or None, document ids that must never appear)
QUESTIONS = [
    ("¿Cuándo hay que entregar el proyecto final de RAG?", "brief-rag", {"brief-vision"}),
    ("¿Qué días son las clases presenciales?", "calendario-v2", {"calendario-v1"}),
    ("¿Cuándo se entrega el proyecto de visión por computador?", None, {"brief-vision"}),
]


def embed(client: httpx.Client, text: str, task: str) -> list[float]:
    response = client.post(
        EMBED_URL,
        json={
            "model": f"models/{EMBED_MODEL}",
            "content": {"parts": [{"text": text}]},
            "taskType": task,
            "outputDimensionality": EMBED_DIM,
        },
    )
    response.raise_for_status()
    values = response.json()["embedding"]["values"]
    if len(values) != EMBED_DIM:
        raise RuntimeError(f"Expected {EMBED_DIM} dimensions, got {len(values)}")
    return values


def as_vector(values: list[float]) -> str:
    return "[" + ",".join(f"{v:.7f}" for v in values) + "]"


def main() -> int:
    db_url = os.environ.get("GISTAR_TEST_DATABASE_URL", "")
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not db_url or not api_key:
        print("Missing GISTAR_TEST_DATABASE_URL or GEMINI_API_KEY (see the usage notes).")
        return 2
    db_url = db_url.replace("postgresql+psycopg://", "postgresql://", 1)

    failures = 0
    with httpx.Client(timeout=30, headers={"x-goog-api-key": api_key}) as client, psycopg.connect(
        db_url
    ) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.execute(
            f"""
            CREATE TEMP TABLE smoke_chunk (
                doc_id text, cohort text, title text, version text,
                valid_until date, status text, body text,
                embedding_model text, embedding vector({EMBED_DIM})
            ) ON COMMIT DROP
            """
        )
        for doc_id, cohort, title, version, valid_until, status, text in DOCUMENTS:
            vector = embed(client, text, "RETRIEVAL_DOCUMENT")
            conn.execute(
                "INSERT INTO smoke_chunk VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s::vector)",
                (doc_id, cohort, title, version, valid_until, status, text, EMBED_MODEL,
                 as_vector(vector)),
            )
        print(f"Indexed {len(DOCUMENTS)} synthetic documents with {EMBED_MODEL} ({EMBED_DIM} dims).\n")

        # The scope and freshness filters go in the WHERE clause, so they apply before ranking.
        scope_sql = (
            "cohort = %s AND status = 'vigente' "
            "AND (valid_until IS NULL OR valid_until >= current_date)"
        )
        for question, expected, forbidden in QUESTIONS:
            qvec = as_vector(embed(client, question, "RETRIEVAL_QUERY"))
            rows = conn.execute(
                f"""
                SELECT doc_id, title, version, 1 - (embedding <=> %s::vector) AS similarity
                FROM smoke_chunk WHERE {scope_sql}
                ORDER BY embedding <=> %s::vector LIMIT 3
                """,
                (qvec, USER_COHORT, qvec),
            ).fetchall()
            returned = {r[0] for r in rows}
            top = rows[0] if rows else None
            ok_forbidden = not (returned & forbidden)
            ok_expected = expected is None or (top is not None and top[0] == expected)
            ok = ok_forbidden and ok_expected
            failures += 0 if ok else 1
            print(f"[{'PASS' if ok else 'FAIL'}] {question}")
            for doc_id, title, version, similarity in rows:
                print(f"       {similarity:.3f}  {doc_id}  «{title}», {version}")
            if expected is None:
                print("       (other cohort's document never returned: the assistant must abstain)")
            print()

        rows = conn.execute(
            f"""
            SELECT doc_id FROM smoke_chunk
            WHERE {scope_sql}
              AND to_tsvector('spanish', body) @@ plainto_tsquery('spanish', %s)
            """,
            (USER_COHORT, "clases presenciales"),
        ).fetchall()
        keyword_ok = [r[0] for r in rows] == ["calendario-v2"]
        failures += 0 if keyword_ok else 1
        print(f"[{'PASS' if keyword_ok else 'FAIL'}] Keyword fallback 'clases presenciales' -> "
              f"{[r[0] for r in rows]}")

    print(f"\nResult: {'ALL PASSED' if failures == 0 else f'{failures} FAILED'}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
