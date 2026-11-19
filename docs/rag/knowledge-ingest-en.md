# RAG knowledge ingest (KAN-130)

Spanish version: [knowledge-ingest-es.md](knowledge-ingest-es.md).

Status: implemented and tested locally with synthetic data (PR A). Vectors (embeddings) and the automatic run at container start come in a later PR (PR B).

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
| 1 | Some document was rejected or failed; the others were loaded |
| 2 | The corpus (`corpus.json` broken or missing) or the database cannot be used |

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

`maintained_by` is the area responsible for the document, given as one of the system roles (`admin`, `captacion`, `seleccion`, `coordinacion` or `docente`). Never a person's name.

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

The document text and the value of any personal data are never stored.

## What it does not do yet

- Chunks are stored without a vector. Keyword search already works; semantic search comes with PR B.
- It does not run by itself at container start (PR B).
- There is no document upload from the web. The pipeline (`pipeline.py`) does not depend on where documents come from, so an upload endpoint could reuse it (future work).
- Search, the cohort filter and cited answers are the next task (DA6, KAN-130 and KAN-151).
