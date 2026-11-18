# ADR-0005 · AI assistant technology stack

**Status:** proposed · **Date:** 2026-11-18 (first version: 2026-11-17) · **Owner:** David Rojas · **Jira:** KAN-64, KAN-94, KAN-113 (DA1)

Spanish version: `0005-stack-ia-asistente-es.md`.

## Context

The platform needs an assistant that answers two kinds of questions:

1. **Questions about course documents** (briefs, calendars, criteria), always citing the document the answer comes from.
2. **Operational data**, for example the share of a cohort that has a competency, always within the permissions of the person asking.

Requirements that shape the decision:

- It never makes up an answer: without a source, it abstains.
- It never shows data from another cohort or another person without permission.
- Synthetic data only, at no cost: we are students and there is no budget.
- Render's free plan gives the API 512 MB of memory and 0.1 CPU (official Render documentation, collected in `docs/deploy/KAN-142-render-feasibility.md`).
- The briefing asks for LangChain/LangGraph to orchestrate the RAG system and the agent flows, and LangSmith for traceability.
- If Somos F5 wants to take it to production, switching providers must be easy.

## Decision

| Component | Choice |
|---|---|
| Vector store | PostgreSQL with pgvector (image `pgvector/pgvector:pg16`, already in `infra/compose.yaml`). Cosine distance (`<=>`). Exact search, with no approximate index, while the corpus is small |
| Embeddings | `gemini-embedding-001` through its API, 768-dimension vectors normalised before storage, behind our own interface |
| Search | Hybrid: semantic (pgvector) plus keyword (PostgreSQL full-text search, Spanish configuration), combined |
| Answer generation | Llama 3.3 70B through Groq, using the OpenAI-compatible API format. If it fails, an extractive answer: the retrieved passage with its citation. Every answer states its mode: `generated` or `extractive` |
| Data queries | Fixed read-only tools over Elizabeth's endpoints (EL9, KAN-263), validated with Pydantic. The model never writes SQL |
| Orchestration | Minimal LangGraph with fixed steps inside `api/app/modules/agents/`: classify the question, route to documents or data, check the citation, respond |
| Evaluation | Question bank in `evals/rag/` (PR #14) and a reproducible command. LangSmith only if the team approves the account |

### What "agent" means in this ADR

- A flow with fixed steps that only decides which source to use. It does not act on its own, never writes to the database and never sends anything to anyone.
- Anything the assistant drafts for another person, for example a feedback draft (DA10), is always reviewed and approved by a person.
- This amends item 5 of `docs/01-gap-to-be.md`, which said "Do not do: … agents". It now says "autonomous agents acting without human review". Reason: the briefing asks for LangGraph to orchestrate the RAG system and the agent flows. The change is part of this PR and needs the Product Owner's confirmation.

### Search and permission filter

- The cohort, scope and freshness filter sits in the same SQL query as the search.
- With an approximate index (HNSW), pgvector applies that filter after walking the index, so it can return fewer results than requested, or none. That is why we start with exact search: with a few hundred chunks it takes milliseconds and the filter is always exact.
- If the corpus grows, HNSW (`vector_cosine_ops`) is added with `hnsw.iterative_scan` (pgvector 0.8 or later) and the question bank is run again.

### Information freshness

Course documents change and can become outdated. So that the assistant never answers with expired information:

- Each document stores its **version**, its **valid-from date**, its **review or expiry date**, its **status** (current or obsolete) and a **content hash** to detect changes.
- Search only uses current documents.
- Every answer shows the source and the date of the version used (KAN-264).
- A daily script, with no AI, marks expired documents as obsolete and flags them for review.

### Boundaries by user type

Actual roles in the code (`api/app/core/authz.py`):

| Role | Documents | Data |
|---|---|---|
| `admin` | All | Read-only tools, global scope |
| `docente` | Their cohort's | Their cohort's, once the F3 academic permissions exist |
| `coordinacion` | Their scope's | Aggregates only (percentages and totals), never names |
| `captacion`, `seleccion` | Their call's selection-process documents | None in the first version |
| `coder` (does not exist yet; arrives with F3) | Their cohort's | Their own only; never internal scores or rankings |
| Applicant | Out of the first version | Out of the first version |

- Priority: staff first (teaching and coordination). Learners use the same engine with their own filter, because the briefing asks for an assistant for learners.
- Permissions are checked on the server, never based on what the user claims.
- Every question leaves a record in `audit_event`, the audit table that already exists since F1. The question text is not stored: only the route (documents or data), the documents used, the outcome (answered, no source or denied by scope) and the answer mode.

### Where AI is used and where it is not

AI is used only where judgement is needed: understanding a question, semantic search and writing the answer. Anything that always gives the same result is done with scripts, for example archiving documents or flagging expired ones. That is why an "archivist" agent is dropped.

## Alternatives considered

| Alternative | Reason for rejecting |
|---|---|
| Chroma, Qdrant or FAISS | They add another component to maintain, and the permission filter would live outside PostgreSQL. `docs/01` already rules out Qdrant and Chroma. FAISS stores no metadata and cannot filter by cohort |
| Embedding model inside the API | A good model weighs 1 to 2 GB and does not fit in Render's 512 MB. A small one fits, but retrieves worse |
| Local LLM (Ollama) | Slow without a GPU: high risk during the demo |
| Gemini as the main LLM | Valid, but Groq is faster; it stays available through the same interface |
| RAGAS for evaluation | Needs an LLM judge and uses quota. We start with our own metrics |
| Full LangChain | Large and changes a lot between versions. Only specific pieces would be used if needed |

## Consequences

- **Migration 0003 (DA4, 20/11):** document and chunk tables with a `vector(768)` column, the freshness fields and the model that produced each vector. No HNSW index at first. Switching to a model with a different size would need another migration and reprocessing all documents.
- **Switching providers:** change one configuration variable and run the reindex command. Each chunk stores the model that produced it, because vectors from different models cannot be mixed.
- **External dependency:** if the embedding or LLM API fails, the assistant keeps working with keyword search and the extractive answer.
- **Privacy:** not only the documents but also the questions are sent to Gemini and Groq. The terms of the Gemini API free tier say that Google uses that content to improve its products and ask users not to submit personal information. Connecting it to real data is therefore forbidden, including in a demo with Somos F5. Real data requires the paid tier, an EU-hosted service (GDPR) or a self-hosted model.
- **New variables:** `GEMINI_API_KEY` and `GROQ_API_KEY` in `.env.example` and in `render.yaml` with `sync: false` (Yohanna, YO10).
- **Deployment:** Render's database accepts no connections from the internet (ADR-0008). Document ingestion therefore runs inside the API service and can be repeated at no cost: if a document's hash has not changed, it is not processed again. The 30-day expiry of the free database is already covered in ADR-0008: created on or after 11/11, it lasts beyond the defence.

## Evaluation metrics

- The correct document appears among the top results (Recall@3).
- Faithfulness: the answer says the same as the cited passage.
- Hallucination rate: statements not found in any passage.
- Correct abstention on questions without an answer.
- Zero documents retrieved from another cohort.

All metrics are published, including the bad ones.

## Pending

- **Product Owner confirmation** before 23/11 (DA7): the change to item 5 of `docs/01` and the agents. The first one is the RAG tutor; the feedback reviewer comes with DA10.
- **Adrián's answers** to the questions sent on 17/11 (embeddings, metrics and deployment). If they change anything, this ADR is updated.
- **Compare** Gemini Embedding with a local 768-dimension model using the question bank, before 2/12 (evaluation, KAN-188). Criterion: if Gemini does not beat the local model by at least 5 points of Recall@3, the local one is chosen, as long as it fits in the server's memory.
- **Evidence already delivered:** smoke test in PR #13 and question bank in PR #14.
