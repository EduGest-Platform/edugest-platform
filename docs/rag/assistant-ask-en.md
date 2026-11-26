# Documentation assistant: cited answer or abstention (KAN-130 DA6, KAN-151)

`POST /api/v1/assistant/ask` answers questions about the course documents with the **literal passage** of the document and its **citation**, or says explicitly that **there is no source**. It never makes anything up. Synthetic data only (ADR-0005).

## Contract

Input: `{"question": "...", "cohort_id": "COH-IA"}`. The question has 3 to 500 characters; `cohort_id` is optional and limits the search to one of your cohorts.

Output:

| Field | Meaning |
|---|---|
| `status` | `answered` or `no_source` (abstention: there is no source inside your scope) |
| `mode` | `extractive`: the literal passage. The `generated` mode, written by an LLM, arrives with T10 |
| `retrieval` | `hybrid` (words and meaning) or `keyword` (words only) |
| `answer` | "Según «title» (version): passage", or "No consta en la documentación de tu curso" |
| `citations` | Document, title, version, validity and the passage used |
| `as_of` | Cut-off date: validity is checked on this date (today, in Madrid) |
| `scope_cohorts` | Cohorts that were searched |

## Who can ask (`app/modules/knowledge/scope.py`)

| Profile | Documents |
|---|---|
| Coder | Those of the cohorts of their **active** enrollments. A coder who left sees nothing |
| Teacher and coordination | Those of the cohorts inside their scope (`knowledge.read` permission) |
| Administration | All |
| Recruitment, selection and applicants | None: `403` |

The server decides the scope, never the question. Asking for another cohort with `cohort_id` returns `403`.

## How it searches (`app/modules/knowledge/retrieval.py`)

1. **Scope first.** Only chunks of documents inside the scope, `vigente` and within their validity window, can be candidates. The filter is part of the same SQL query as the search.
2. **Two searches.** By words, with PostgreSQL full-text search in Spanish (stems of 4 or more letters also match as prefixes), and by meaning, with pgvector, when there is a question vector.
3. **Merge with Reciprocal Rank Fusion** (constant 60).
4. **Evidence gate.** A chunk counts if it covers at least 50% of the question's words, weighted by how rare they are in the corpus (IDF), or if its similarity is at least 0.70. If none counts, the assistant abstains.

If Gemini fails, the search continues with words only. Vectors are used only with `GISTAR_RAG_EMBED=true` and `GEMINI_API_KEY`.

## Measurement with the question bank (23 Nov 2026)

24 questions (`evals/rag/questions.jsonl`), reference date 1 Dec 2026. A question with an expected document is right when that document comes first; one without an expected document is right when the assistant abstains.

**Words only** (coverage sweep):

| Minimum coverage | Right | Correct first document | Correct abstention | Wrong answers | Leaks | Obsolete |
|---|---|---|---|---|---|---|
| 0.2 | 19/24 | 14/14 | 5/10 | 5 | 0 | 0 |
| 0.4 | 17/24 | 8/14 | 9/10 | 1 | 0 | 0 |
| **0.5 (chosen)** | **17/24** | **7/14** | **10/10** | **0** | **0** | **0** |
| 0.6 | 15/24 | 5/14 | 10/10 | 0 | 0 | 0 |

**Hybrid, with real Gemini vectors** (coverage 0.5, similarity sweep):

| Minimum similarity | Right | Correct first document | Correct abstention | Wrong answers | Leaks | Obsolete |
|---|---|---|---|---|---|---|
| 0.60 | 18/24 | 14/14 | 4/10 | 6 | 0 | 0 |
| 0.65 | 24/24 | 14/14 | 10/10 | 0 | 0 | 0 |
| **0.70 (chosen)** | **22/24** | **12/14** | **10/10** | **0** | **0** | **0** |
| 0.75 | 18/24 | 8/14 | 10/10 | 0 | 0 | 0 |

0.70 is chosen over 0.65 on purpose: the 24/24 comes from the same bank used for tuning (overfitting), and there are unanswerable questions between 0.60 and 0.65. 0.70 leaves a margin and only costs two extra abstentions (q10 and q12). Under ADR-0005, abstaining is better than answering with the wrong passage.

## Known limits

- **Synonyms in words-only mode.** "Fecha límite" does not find "Entrega": the words-only mode abstains more (7/14 answered). The hybrid mode covers it (12/14).
- **Overfitting.** The thresholds were tuned on the same bank that measures them. KAN-188 should add new questions before moving them again.
- **Staging.** Vectors are on (`GISTAR_RAG_EMBED=true`) and need `GEMINI_API_KEY` in the Render dashboard. Without the key, or if Gemini fails, the assistant searches by keywords only.
- **No generation.** The answer is the literal passage; the `generated` mode with citation checking arrives with T10.

## Audit

Each question leaves an `assistant.ask` row with the outcome (`answered`, `no_source` or `forbidden`), the search mode, the documents used and, if any, the Gemini error code. **The text of the question is never stored.**

## Repeat the measurement

From `api/`, always against a disposable database (for example the test one), because it runs the ingest:

```sh
GISTAR_DATABASE_URL=<test database> python -m app.modules.knowledge.evaluate --sweep            # words only
GISTAR_DATABASE_URL=<test database> python -m app.modules.knowledge.evaluate --hybrid --sweep   # real vectors
```

`--hybrid` only sends the synthetic corpus and questions to Gemini, with the key in `api/.env`. Each question is sent once.
