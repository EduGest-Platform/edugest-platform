"""KAN-130 DA6 / KAN-151: POST /assistant/ask answers with a citation or abstains, inside the caller's scope only."""

import json
from datetime import date

import pytest
from sqlalchemy import select, text, update

from app.core.config import settings
from app.modules.assistant import router as assistant_router
from app.modules.audit.models import AuditEvent
from app.modules.identity.models import User
from app.modules.knowledge.ingest import run_ingest
from app.modules.learning.models import Enrollment
from tests.conftest import ASPIRANTE, CAPT_IA, CODER, DOCENTE, login

URL = "/api/v1/assistant/ask"
LATE_RECIPE = "Si entrego el Recetario un día tarde, ¿me lo aceptan?"  # q04: answered from A1 in keyword mode
PESTS = "¿Cuándo se entrega el proyecto de las plagas?"  # q19: cohort B only


@pytest.fixture(autouse=True)
def corpus(db, monkeypatch):
    monkeypatch.setattr(settings, "rag_embed", False)  # never call Gemini from the tests, whatever api/.env says
    monkeypatch.setattr(assistant_router, "today", lambda: date(2026, 12, 1))  # the bank's reference date
    db.execute(text("TRUNCATE knowledge_chunk, knowledge_document"))
    db.commit()
    run_ingest(db, settings.corpus_path)


def ask(client, headers, question, **extra):
    return client.post(URL, json={"question": question, **extra}, headers=headers)


def test_coder_gets_an_extractive_answer_with_its_citation(client):
    r = ask(client, login(client, CODER), LATE_RECIPE)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "answered" and body["mode"] == "extractive" and body["retrieval"] == "keyword"
    [citation] = body["citations"]
    assert citation["source_key"] == "A1" and citation["version"] == "v1" and "24 horas" in citation["excerpt"]
    assert body["as_of"] == "2026-12-01" and body["scope_cohorts"] == ["COH-IA"]


def test_question_about_another_cohort_abstains(client):
    body = ask(client, login(client, CODER), PESTS).json()
    assert body["status"] == "no_source" and body["citations"] == [] and "No consta" in body["answer"]


def test_coder_cannot_choose_a_cohort_that_is_not_its_own(client):
    assert ask(client, login(client, CODER), LATE_RECIPE, cohort_id="COH-DATA").status_code == 403


@pytest.mark.parametrize("email", [CAPT_IA, ASPIRANTE])
def test_roles_without_documents_get_403(client, email):
    assert ask(client, login(client, email), LATE_RECIPE).status_code == 403


def test_coder_who_left_gets_403(client, db):
    coder = db.scalar(select(User).where(User.email == CODER))
    db.execute(update(Enrollment).where(Enrollment.person_id == coder.person_id).values(estado="baja_voluntaria"))
    db.commit()
    assert ask(client, login(client, CODER), LATE_RECIPE).status_code == 403


def test_without_session_gets_401(client):
    assert client.post(URL, json={"question": LATE_RECIPE}).status_code == 401


def test_teacher_can_narrow_the_search_to_one_of_its_cohorts(client):
    body = ask(client, login(client, DOCENTE), LATE_RECIPE, cohort_id="COH-DATA").json()
    assert body["scope_cohorts"] == ["COH-DATA"] and body["status"] == "no_source"


def test_audit_never_stores_the_question(client, db):
    ask(client, login(client, CODER), LATE_RECIPE)
    event = db.scalar(select(AuditEvent).where(AuditEvent.action == "assistant.ask"))
    assert event.meta["result"] == "answered" and event.meta["documents"] == ["A1"]
    assert "Recetario" not in json.dumps(event.meta, ensure_ascii=False)


def test_too_long_question_is_rejected(client):
    assert ask(client, login(client, CODER), "a" * 501).status_code == 422


def stream_events(response):
    assert response.headers["content-type"].startswith("text/event-stream")
    return [
        (lines[0].removeprefix("event: "), json.loads(lines[1].removeprefix("data: ")))
        for frame in response.text.strip().split("\n\n")
        if (lines := frame.splitlines())
    ]


def test_stream_delivers_the_authorized_answer_and_citation_once(client, db):
    response = client.post(f"{URL}/stream", headers=login(client, CODER), json={"question": LATE_RECIPE})
    assert response.status_code == 200
    assert "no-store" in response.headers["cache-control"]
    events = stream_events(response)
    assert events[0] == ("phase", {"source_kind": "documents"})
    assert events[-1][0] == "answer"
    answer = events[-1][1]
    assert answer["citations"][0]["source_key"] == "A1"
    assert "".join(data["text"] for event, data in events[1:-1] if event == "delta") == answer["answer"]
    [entry] = db.scalars(select(AuditEvent).where(AuditEvent.action == "assistant.ask"))
    assert entry.meta["result"] == "answered" and LATE_RECIPE not in str(entry.meta)


def test_stream_rejects_foreign_cohort_before_sending_events(client):
    body = {"question": LATE_RECIPE, "cohort_id": "COH-DATA"}
    assert client.post(f"{URL}/stream", json=body).status_code == 401
    response = client.post(f"{URL}/stream", headers=login(client, CODER), json=body)
    assert response.status_code == 403 and "text/event-stream" not in response.headers["content-type"]


def test_stream_ends_with_generic_error_when_retrieval_fails(client, monkeypatch):
    def unavailable(*args, **kwargs):
        raise RuntimeError("synthetic internal error")
    monkeypatch.setattr(assistant_router, "retrieve", unavailable)

    response = client.post(f"{URL}/stream", headers=login(client, CODER), json={"question": LATE_RECIPE})
    assert stream_events(response) == [
        ("phase", {"source_kind": "documents"}),
        ("error", {"code": "assistant_unavailable"}),
    ]
    assert "synthetic internal error" not in response.text
