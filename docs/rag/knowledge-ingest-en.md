# RAG knowledge ingest (KAN-130)

Spanish version: [knowledge-ingest-es.md](knowledge-ingest-es.md).

Status: implemented and tested locally with synthetic data. It includes the vectors (embeddings) with Gemini and the automatic run at container start.

## What it does

It loads the course documents in `evals/rag/corpus/` into the `knowledge_document` and `knowledge_chunk` tables, so the assistant can search them filtered by cohort and validity.

It is safe and repeatable:

- **No personal data.** A document with an email, a DNI or NIE, a phone number or the full name of a registered person is rejected whole. The message names the kind of data, never the value.
- **Repeatable.** Each document stores a fingerprint (SHA-256) of its text. If nothing changed, nothing is done.
- **Never deletes.** A document that leaves the corpus, or gets a new version, is marked `obsoleto`. This keeps a record of what information existed.
- **Audited.** Every real change writes an `audit_event` row with codes and IDs only.
- **Atomic.** One transaction per document: if something fails, that document is rolled back whole.

## How to run it

From the `api/` folder, with the database running and migrated (`alembic upgrade head`):

```bash
python -m app.modules.knowledge.ingest            # real ingest
python -m app.modules.knowledge.ingest --dry-run  # dry run: does everything and saves nothing
```

Options: `--corpus PATH` to use another folder. The default is `GISTAR_CORPUS_PATH`, which points to `evals/rag/corpus` locally.

When it finishes it prints one row per document (version, cohort, status, validity, action, chunks, vector and owner) and a summary with the reason of each rejection.

| Exit code | Meaning |
|---|---|
| 0 | Everything was loaded or nothing had changed |
| 1 | Some document was rejected or failed, or vectors are missing (the provider failed or the key is missing); the others were loaded |
| 2 | The corpus (`corpus.json` broken or missing) or the database cannot be used |

## Vectors (embeddings)

With `GISTAR_RAG_EMBED=true` and `GEMINI_API_KEY` set, the ingest computes one vector per chunk with `gemini-embedding-001` (768 dimensions, normalized), for semantic search. Without those two variables, it stores the text without vectors and keyword search keeps working.

- **Only what is needed.** Vectors are requested only for new chunks, changed chunks or chunks computed with another model. If nothing changes, no call is made.
- **No personal data.** Only documents that already passed the personal-data check are sent.
- **Fault tolerant.** On usage limits or temporary errors (429, 500, 503 or a network failure) it retries up to 3 times. If it still fails, it stores the text without vectors, shows it in the report with a code (for example `http_429`) and ends with exit code 1. The next run tries again.
- **Codes only in errors.** The key and the document text are never printed or stored.
- `--dry-run` never calls the provider.

The key lives only in `api/.env` locally and in the Render dashboard when deployed. Never in the repository.

## At container start

`api/docker-entrypoint.sh` runs the ingest after the migrations and the seed. It never stops the API from starting: if it fails, rejects a document or takes more than 3 minutes, it logs a warning and the API starts with the knowledge it already had.

The corpus ships inside the image (`/data/corpus`, with `GISTAR_CORPUS_PATH`). Locally, Docker Compose mounts the `evals/rag/corpus` folder over it, so the version you are editing is used.

On staging (`render.staging.yaml`), vectors are enabled (`GISTAR_RAG_EMBED: "true"`, since 26/11/2026). `GEMINI_API_KEY` is set only in the Render dashboard; without it, the ingest stores text without vectors and search stays keyword-only. Documents already loaded get their vectors on the next start.

## What happens to each document

| Action | When |
|---|---|
| created (`nuevo`) | The document did not exist in that version |
| updated (`actualizado`) | Its text changed (its chunks are replaced), or only its data such as status or dates (no rechunking) |
| unchanged (`sin cambios`) | Same text and same data. Not audited |
| rejected (`rechazado`) | Personal data, no content to index, or an incomplete entry in `corpus.json` |
| retired (`retirado`) | It left the corpus or has a new version. It stays as `obsoleto` |

A badly written `corpus.json` entry never retires the version already stored: a typo does not make a good document disappear.

## How to add, change or retire a document

1. **Add:** create the `.md` file in `evals/rag/corpus/` and add its entry to `corpus.json` with `id`, `file`, `title`, `cohort` (`A` or `B`), `version`, `valid_from`, `valid_until` (optional), `status` (`vigente` or `obsoleto`), `synthetic: true` and `maintained_by`.
2. **Change the text:** edit the `.md`. For an important change, also raise the `version` to keep the previous one as history.
3. **Retire:** set `status: "obsoleto"` or remove the entry. The document is not deleted.
4. Run the ingest and check the report.

The `id` follows the corpus format: 1 to 4 letters and 1 to 3 digits (`A1`, `B12`). The `version` is a `v` and 1 to 3 digits (`v1`, `v10`). This way no identifier can hold a DNI or a phone number.

`maintained_by` is the area responsible for the document, given as a role and never as a person's name. Only `docente` is accepted: the assistant is fed exclusively with materials shared by teachers (Melissa, round 3, Q16, and Q15 approved by the PO on 23/11/2026). The ingest rejects any other value with a reason.

Each corpus cohort maps to the real seed cohort in `app/modules/knowledge/corpus.py` (`COHORT_SCOPE`). A test fails if those cohorts stop existing.

## Personal data: what it detects and its limits

It detects emails, DNI or NIE, Spanish phone numbers and the full names (two or more words) of the people registered in the database, ignoring case and accents.

Limit: a single first name, or the name of an unregistered person, is not detected. Checking single names would reject ordinary documents. For production, adding an entity detector such as Microsoft Presidio is proposed (future work, not implemented).

## Audit

| Event | Stored data |
|---|---|
| `knowledge.document.created` / `updated` | document, version, status and number of chunks |
| `knowledge.document.rejected` | document, version, reason (`personal_data` or `no_content`) and kinds of data found |
| `knowledge.document.retired` | document and version |
| `knowledge.document.embedded` | document, version, model and number of chunks with a new vector |

The document text and the value of any personal data are never stored.

## What it does not do yet

- On staging, vectors start disabled until the Gemini key is set in Render.
- There is no document upload from the web. The pipeline (`pipeline.py`) does not depend on where documents come from, so an upload endpoint could reuse it (future work).
- Search, the cohort filter and cited answers are the next task (DA6, KAN-130 and KAN-151).
