"""KAN-130: knowledge ingest against PostgreSQL. Repeatable, fail-closed on personal data, never deletes, audited."""

import json
import shutil

import pytest
from sqlalchemy import func, select, text

from app.core.config import settings
from app.modules.audit.models import AuditEvent
from app.modules.identity.models import Person
from app.modules.knowledge.ingest import main, run_ingest
from app.modules.knowledge.models import KnowledgeChunk, KnowledgeDocument

EMAIL = "tutoria@example.test"


@pytest.fixture(autouse=True)
def _empty_knowledge(_fresh_data, db):
    # The seed reset does not cover the RAG tables (and #46 changes that line): clean them here.
    db.execute(text("TRUNCATE knowledge_chunk, knowledge_document"))
    db.commit()


@pytest.fixture
def corpus(tmp_path):
    folder = tmp_path / "corpus"
    shutil.copytree(settings.corpus_path, folder)
    return folder


def edit_manifest(folder, change):
    path = folder / "corpus.json"
    entries = change(json.loads(path.read_text(encoding="utf-8")))
    path.write_text(json.dumps(entries, ensure_ascii=False), encoding="utf-8")


def update_entry(folder, key, **changes):
    edit_manifest(folder, lambda entries: [{**e, **changes} if e["id"] == key else e for e in entries])


def actions(results):
    return {(r.source_key, r.version): r.action for r in results}


def stored(db, key, version):
    db.expire_all()
    return db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.source_key == key, KnowledgeDocument.version == version))


def chunk_ids(db, key):
    db.expire_all()
    rows = db.scalars(select(KnowledgeChunk.id).join(KnowledgeDocument).where(KnowledgeDocument.source_key == key).order_by(KnowledgeChunk.ordinal))
    return list(rows)


def knowledge_audit_count(db):
    return db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action.like("knowledge.%")))


def test_first_run_creates_every_document_with_its_scope_and_chunks_without_vectors(db, corpus):  # CA1, CA6
    results = run_ingest(db, str(corpus))
    assert set(actions(results).values()) == {"created"} and len(results) == 6
    db.expire_all()
    documents = {d.source_key: d for d in db.scalars(select(KnowledgeDocument))}
    assert {k: d.scope_id for k, d in documents.items()} == {
        "A1": "COH-IA", "A2": "COH-IA", "A3": "COH-IA", "A4": "COH-IA", "A5": "COH-IA", "B1": "COH-DATA",
    }
    assert documents["A3"].status == "obsoleto" and all(len(d.content_hash) == 64 for d in documents.values())
    chunks = list(db.scalars(select(KnowledgeChunk)))
    assert len(chunks) == 25
    assert all(c.embedding is None and c.embedding_model is None for c in chunks)


def test_second_run_changes_nothing_and_audits_nothing(db, corpus):  # CA2
    run_ingest(db, str(corpus))
    before_ids, before_audit = chunk_ids(db, "A4"), knowledge_audit_count(db)
    results = run_ingest(db, str(corpus))
    assert set(actions(results).values()) == {"unchanged"}
    assert chunk_ids(db, "A4") == before_ids
    assert knowledge_audit_count(db) == before_audit


def test_changed_text_replaces_only_that_documents_chunks(db, corpus):  # CA3
    run_ingest(db, str(corpus))
    others = {key: chunk_ids(db, key) for key in ("A1", "A2", "A5", "B1")}
    with (corpus / "A4-normas-asistencia.md").open("a", encoding="utf-8") as f:
        f.write("\nLas tutorías se piden con dos días de antelación.\n")
    results = run_ingest(db, str(corpus))
    assert actions(results)[("A4", "v1")] == "updated"
    assert len(chunk_ids(db, "A4")) == 6
    assert {key: chunk_ids(db, key) for key in others} == others


def test_a_metadata_change_updates_without_rechunking(db, corpus):
    run_ingest(db, str(corpus))
    before = chunk_ids(db, "A2")
    update_entry(corpus, "A2", status="obsoleto")
    assert actions(run_ingest(db, str(corpus)))[("A2", "v2")] == "updated"
    assert stored(db, "A2", "v2").status == "obsoleto"
    assert chunk_ids(db, "A2") == before


def test_a_new_version_keeps_the_old_one_as_obsolete(db, corpus):  # CA4
    run_ingest(db, str(corpus))
    update_entry(corpus, "A2", version="v3")
    result = actions(run_ingest(db, str(corpus)))
    assert result[("A2", "v3")] == "created" and result[("A2", "v2")] == "retired"
    assert stored(db, "A2", "v2").status == "obsoleto" and stored(db, "A2", "v3").status == "vigente"


def test_a_document_removed_from_the_corpus_is_retired_never_deleted(db, corpus):
    run_ingest(db, str(corpus))
    edit_manifest(corpus, lambda entries: [e for e in entries if e["id"] != "B1"])
    assert actions(run_ingest(db, str(corpus)))[("B1", "v1")] == "retired"
    assert stored(db, "B1", "v1").status == "obsoleto"
    assert len(chunk_ids(db, "B1")) == 4


def test_personal_data_rejects_the_whole_document_and_is_never_shown(db, corpus, capsys):  # CA5
    with (corpus / "A5-criterios-evaluacion.md").open("a", encoding="utf-8") as f:
        f.write(f"\nDudas: {EMAIL}\n")
    assert main(["--corpus", str(corpus)]) == 1
    report = capsys.readouterr().out
    assert "A5: personal data: email" in report and EMAIL not in report
    assert stored(db, "A5", "v1") is None and stored(db, "A4", "v1") is not None
    event = db.scalar(select(AuditEvent).where(AuditEvent.action == "knowledge.document.rejected"))
    assert event.meta == {"source_key": "A5", "version": "v1", "reason": "personal_data", "kinds": ["email"]}
    assert EMAIL not in json.dumps(event.meta)


def test_a_registered_persons_full_name_rejects_the_document(db, corpus):  # CA5
    name = next(n for n in db.scalars(select(Person.display_name)) if len(n.split()) >= 2)
    with (corpus / "A1-brief-recetario.md").open("a", encoding="utf-8") as f:
        f.write(f"\nPresenta: {name}.\n")
    result = next(r for r in run_ingest(db, str(corpus)) if r.source_key == "A1")
    assert result.action == "rejected" and result.reason == "personal data: person_name"


def test_an_unreadable_entry_is_reported_and_its_stored_version_is_not_retired(db, corpus):  # CA12
    run_ingest(db, str(corpus))
    edit_manifest(corpus, lambda entries: [{k: v for k, v in e.items() if not (e["id"] == "A4" and k == "maintained_by")} for e in entries])
    result = next(r for r in run_ingest(db, str(corpus)) if r.source_key == "A4")
    assert result.action == "rejected" and "maintained_by" in result.reason
    assert stored(db, "A4", "v1").status == "vigente"


def test_a_document_without_content_is_rejected(db, corpus):
    (corpus / "A1-brief-recetario.md").write_text("# Brief del proyecto\n\n## Vacío\n", encoding="utf-8")
    result = next(r for r in run_ingest(db, str(corpus)) if r.source_key == "A1")
    assert result.action == "rejected" and result.reason == "no content to index"
    assert stored(db, "A1", "v1") is None


def test_a_dry_run_saves_and_audits_nothing(db, corpus):
    results = run_ingest(db, str(corpus), dry_run=True)
    assert set(actions(results).values()) == {"created"}
    assert stored(db, "A1", "v1") is None and knowledge_audit_count(db) == 0


def test_audit_events_carry_only_codes_and_ids(db, corpus):  # CA11
    run_ingest(db, str(corpus))
    events = list(db.scalars(select(AuditEvent).where(AuditEvent.action.like("knowledge.%"))))
    assert len(events) == 6 and {e.action for e in events} == {"knowledge.document.created"}
    assert all(set(e.meta) == {"source_key", "version", "status", "chunks"} and e.actor_user_id is None for e in events)


def test_the_report_lists_every_document_and_a_summary(corpus, capsys):  # CA10
    assert main(["--corpus", str(corpus)]) == 0
    report = capsys.readouterr().out
    assert "Responsable" in report and "Resumen: 6 documentos · 6 nuevo" in report
    assert all(f"\n{key} " in report for key in ("A1", "A2", "A3", "A4", "A5", "B1"))


def test_a_broken_manifest_exits_with_2(corpus):
    (corpus / "corpus.json").write_text("{not json", encoding="utf-8")
    assert main(["--corpus", str(corpus)]) == 2


def test_a_rejected_new_version_never_retires_the_current_one(db, corpus):  # review #51, point 1
    run_ingest(db, str(corpus))
    update_entry(corpus, "A2", version="v3")
    with (corpus / "A2-calendario-v2.md").open("a", encoding="utf-8") as f:
        f.write(f"\nDudas: {EMAIL}\n")
    assert actions(run_ingest(db, str(corpus)))[("A2", "v3")] == "rejected"
    assert stored(db, "A2", "v2").status == "vigente" and stored(db, "A2", "v3") is None


def test_a_failed_new_version_never_retires_the_current_one(db, corpus, monkeypatch):  # review #51, point 1
    import app.modules.knowledge.ingest as ingest_module
    from sqlalchemy.exc import SQLAlchemyError

    run_ingest(db, str(corpus))
    update_entry(corpus, "A2", version="v3")
    real = ingest_module.ingest_document

    def fails_for_a2(session, doc, names):
        if doc.source_key == "A2":
            raise SQLAlchemyError("synthetic failure")
        return real(session, doc, names)

    monkeypatch.setattr(ingest_module, "ingest_document", fails_for_a2)
    assert actions(run_ingest(db, str(corpus)))[("A2", "v3")] == "failed"
    assert stored(db, "A2", "v2").status == "vigente"


def test_personal_data_in_the_title_is_never_stored_audited_or_printed(db, corpus, capsys):  # review #51, point 2
    update_entry(corpus, "A1", title=f"Brief de {EMAIL}")
    assert main(["--corpus", str(corpus)]) == 1
    assert EMAIL not in capsys.readouterr().out
    db.expire_all()
    assert stored(db, "A1", "v1") is None
    assert not any(EMAIL in chunk for chunk in db.scalars(select(KnowledgeChunk.text)))
    assert all(EMAIL not in json.dumps(e.meta) for e in db.scalars(select(AuditEvent)))


def test_a_title_change_rewrites_every_chunk(db, corpus):  # review #51, point 3
    run_ingest(db, str(corpus))
    update_entry(corpus, "A4", title="Normas de asistencia revisadas")
    assert actions(run_ingest(db, str(corpus)))[("A4", "v1")] == "updated"
    db.expire_all()
    texts = list(db.scalars(select(KnowledgeChunk.text).join(KnowledgeDocument).where(KnowledgeDocument.source_key == "A4")))
    # Every chunk carries the new title (the old in-file heading now reads as a section, which is expected).
    assert texts and all(t.startswith("Normas de asistencia revisadas") for t in texts)


def test_a_failure_while_rejecting_never_prints_the_title(corpus, capsys, monkeypatch):  # review #51, point 5
    from sqlalchemy.exc import SQLAlchemyError

    from app.core import audit

    real = audit.record

    def fails_on_rejection(db, actor, action, *args, **kwargs):
        if action == "knowledge.document.rejected":
            raise SQLAlchemyError("synthetic failure")
        return real(db, actor, action, *args, **kwargs)

    monkeypatch.setattr(audit, "record", fails_on_rejection)
    update_entry(corpus, "A1", title=f"Brief de {EMAIL}")
    assert main(["--corpus", str(corpus)]) == 1
    report = capsys.readouterr().out
    assert "A1: SQLAlchemyError" in report and EMAIL not in report
