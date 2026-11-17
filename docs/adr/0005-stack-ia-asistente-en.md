# ADR-0005 · AI assistant technology stack

**Status:** proposed · **Date:** 2026-11-17 · **Owner:** David Rojas · **Jira:** KAN-64, KAN-94, KAN-113 (DA1)

Spanish version: `0005-stack-ia-asistente-es.md`.

## Context

The platform needs an assistant that answers two kinds of questions:

1. **Questions about course documents** (briefs, calendars, criteria), always citing the document the answer comes from.
2. **Operational data**, for example how many absences a person has, always within the permissions of the person asking.

Requirements that shape the decision:

- It never makes up an answer: without a source, it abstains.
- It never shows data from another cohort or another person without permission.
- Synthetic data only, at no cost: we are students and there is no budget.
- Render's free instance has 512 MB of memory for the whole API (ADR-0008).
- If Somos F5 wants to take it to production, switching providers must be easy.

## Decision

| Component | Choice |
|---|---|
| Vector store | PostgreSQL with pgvector (already in `infra/compose.yaml`), with an HNSW index |
| Embeddings | Gemini Embedding through its API, 768-dimension vectors, behind our own interface |
| Search | Hybrid: semantic (pgvector) plus keyword (PostgreSQL full-text search, Spanish configuration), combined |
| Answer generation | Llama 3.3 70B through Groq, using the OpenAI-compatible API format. If it fails, an extractive answer: the retrieved passage with its citation |
| Data queries | Fixed read-only tools over Elizabeth's endpoints (EL9, KAN-263), validated with Pydantic. The model never writes SQL |
| Orchestration | Minimal LangGraph inside `api/app/modules/agents/`: classify the question, route to documents or data, check the answer, respond |
| Evaluation | A bank of 20 to 30 questions in `evals/rag/` and a reproducible command. LangSmith only if the team approves the account |

### Information freshness

Course documents change and can become outdated. So that the assistant never answers with expired information:

- Each document stores its **version**, its **valid-from date**, its **review or expiry date**, its **status** (current or obsolete) and a **content hash** to detect changes.
- Search only uses current documents.
- Every answer shows the source and the date of the version used (KAN-264).
- A daily script, with no AI, marks expired documents as obsolete and flags them for review.

### Boundaries by user type

- Permissions are checked on the server, never based on what the user claims.
- The cohort and scope filter is applied **before** searching.
- Separate instructions and tools per user type: a coder or applicant only sees their own data and never internal scores or rankings; Somos F5 staff can compare within their scope.
- Every question leaves an audit record (`audit_event`), storing no more personal data than needed.

### Where AI is used and where it is not

AI is used only where judgement is needed: understanding a question, semantic search and writing the answer. Anything that always gives the same result is done with scripts, for example archiving documents or flagging expired ones. That is why an "archivist" agent is dropped.

## Alternatives considered

| Alternative | Reason for rejecting |
|---|---|
| Chroma, Qdrant or FAISS | They add another component to maintain, and the permission filter would live outside PostgreSQL. `docs/01` already rules out new services. FAISS stores no metadata and cannot filter by cohort |
| Embedding model inside the API | A good model weighs 1 to 2 GB and does not fit in Render's 512 MB. A small one fits, but retrieves worse |
| Local LLM (Ollama) | Slow without a GPU: high risk during the demo |
| Gemini as the main LLM | Valid, but Groq is faster; it stays available through the same interface |
| RAGAS for evaluation | Needs an LLM judge and uses quota. We start with our own metrics |
| Full LangChain | Large and changes a lot between versions. Only specific pieces would be used if needed |

## Consequences

- **Migration 0003 (DA4, 20/11):** document and chunk tables with a 768-dimension vector column and the freshness fields. Switching to a model with a different size would need another migration and reprocessing all documents.
- **Switching providers:** change one configuration variable and run the reindex command. Each chunk stores the model that produced it, because vectors from different models cannot be mixed.
- **External dependency:** if the embedding or LLM API fails, the assistant keeps working with keyword search and the extractive answer.
- **Data:** the free tiers of Gemini and Groq are for the demo with synthetic data only. Real data requires the paid tier or an EU-hosted service (GDPR), or a self-hosted model on a server with more memory.
- **New variables:** `GEMINI_API_KEY` and `GROQ_API_KEY` in `.env.example` and in Render (Yohanna, YO10).
- **Deployment (suggestion for ADR-0008):** Render's free PostgreSQL expires after 30 days; Neon is free, supports pgvector and does not expire. The decision belongs to Yohanna.

## Evaluation metrics

- The correct document appears among the top results.
- Faithfulness: the answer says the same as the cited passage.
- Hallucination rate: statements not found in any passage.
- Correct abstention on questions without an answer.
- Zero documents retrieved from another cohort.

All metrics are published, including the bad ones.

## Pending

- Smoke test: index three synthetic documents and retrieve the right one with its citation. Delivered in a separate PR.
- Adrián's answers to the questions sent on 17/11 (embeddings, metrics and deployment).
- Product Owner confirmation on the agents before 23/11 (DA7). The first one is the RAG tutor; the feedback reviewer comes with DA10.
- Compare Gemini Embedding with a local model of the same size using the question bank before closing the decision.
