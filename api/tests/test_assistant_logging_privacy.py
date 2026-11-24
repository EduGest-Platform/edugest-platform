"""KAN-209: question text is absent from assistant audit and captured operational logs."""

import json
import logging
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.core.config import settings
from app.core.error_handling import REQUEST_ID_HEADER
from app.main import app
from app.modules.assistant import router as assistant_router
from app.modules.audit.models import AuditEvent
from app.modules.knowledge.ingest import run_ingest
from tests.conftest import CODER, login

QUESTION = "Si entrego el Recetario un día tarde, ¿me lo aceptan?"
OTHER_COURSE = "¿Cuándo se entrega el proyecto de las plagas?"
FAILURE_MARKER = "synthetic-private-retrieval-error-marker"


@pytest.fixture
def corpus(db, monkeypatch):
    monkeypatch.setattr(settings, "rag_embed", False)
    monkeypatch.setattr(assistant_router, "today", lambda: date(2026, 12, 1))
    db.execute(text("TRUNCATE knowledge_chunk, knowledge_document"))
    db.commit()
    run_ingest(db, settings.corpus_path)


def assert_safe_logs(caplog, response, question):
    correlation = response.headers[REQUEST_ID_HEADER]
    assert correlation
    messages = [record.getMessage() for record in caplog.records if record.name == "app.access"]
    assert any("/assistant/ask" in message and correlation in message for message in messages)
    assert question not in caplog.text
    if response.status_code >= 400:
        assert question not in response.text


@pytest.mark.parametrize("question,cohort,status,result", [
    (QUESTION, None, 200, "answered"),
    (OTHER_COURSE, None, 200, "no_source"),
    (QUESTION, "COH-DATA", 403, "forbidden"),
])
def test_question_is_not_copied_to_logs_or_audit_on_answer_abstention_or_denial(client, db, corpus, caplog,
                                                                            question, cohort, status, result):
    token = login(client, CODER)
    caplog.set_level(logging.INFO)
    caplog.clear()
    body = {"question": question, **({"cohort_id": cohort} if cohort else {})}
    response = client.post("/api/v1/assistant/ask", headers=token, json=body)
    assert response.status_code == status
    if status == 200:
        assert response.json()["status"] == result
    assert_safe_logs(caplog, response, question)
    events = list(db.scalars(select(AuditEvent).where(AuditEvent.action == "assistant.ask")))
    assert len(events) == 1 and events[0].meta["result"] == result
    assert question not in json.dumps(events[0].meta, ensure_ascii=False)


def test_rejected_question_is_not_echoed_by_validation_or_logs(client, db, corpus, caplog):
    token = login(client, CODER)
    caplog.set_level(logging.INFO)
    caplog.clear()
    question = "synthetic-private-validation-marker-" * 30
    response = client.post("/api/v1/assistant/ask", headers=token, json={"question": question})
    assert response.status_code == 422
    assert_safe_logs(caplog, response, question)
    assert "synthetic-private-validation-marker" not in response.text + caplog.text
    assert not list(db.scalars(select(AuditEvent).where(AuditEvent.action == "assistant.ask")))


def test_retrieval_failure_keeps_question_and_exception_message_out_of_logs(client, db, corpus, monkeypatch, caplog):
    token = login(client, CODER)

    def fail(*_args, **_kwargs):
        raise RuntimeError(FAILURE_MARKER + QUESTION)

    monkeypatch.setattr(assistant_router, "retrieve", fail)
    caplog.set_level(logging.INFO)
    caplog.clear()
    with TestClient(app, raise_server_exceptions=False) as failing_client:
        response = failing_client.post("/api/v1/assistant/ask", headers=token, json={"question": QUESTION})
    assert response.status_code == 500
    assert_safe_logs(caplog, response, QUESTION)
    assert FAILURE_MARKER not in response.text + caplog.text
    assert any("RuntimeError" in record.getMessage() for record in caplog.records)
    assert not list(db.scalars(select(AuditEvent).where(AuditEvent.action == "assistant.ask")))
