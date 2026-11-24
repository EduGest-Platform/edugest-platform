"""KAN-195 / KAN-61 / KAN-62 / KAN-202 / KAN-264: the assistant answers record questions with the read-only tools.

Records only for staff with permission and for questions that ask for figures about one topic; everything else
keeps going to the documents. Answers are cohort totals with source and time, never names or per-person rows.
"""

import json
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.db import utcnow
from app.main import app
from app.modules.assistant import records
from app.modules.assistant.router import CHOOSE_COHORT
from app.modules.audit.models import AuditEvent
from app.modules.learning.models import Enrollment
from app.seed import load_seed
from app.seed_academic import load_academic
from tests.conftest import CODER, COORD, DOCENTE, login

COHORT, OTHER = "COH-IA", "COH-DATA"
ATTENDANCE_QUESTION = "¿Cuántas faltas hay en la cohorte?"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setattr(settings, "rag_embed", False)


def ask(client, token, question, cohort_id=None):
    body = {"question": question, **({"cohort_id": cohort_id} if cohort_id else {})}
    return client.post("/api/v1/assistant/ask", headers=token, json=body)


@pytest.mark.parametrize("question,topic", [
    ("¿Cuántas faltas hay en COH-IA?", "attendance"),
    ("Dame un resumen de la asistencia", "attendance"),
    ("¿Quién tiene entregas vencidas?", "submissions"),
    ("¿Cuántos coders hay en cada nivel de competencias?", "competencies"),
    ("Si entrego el Recetario un día tarde, ¿me lo aceptan?", None),  # KAN-207: a rules question stays in documents
    ("¿Cuántas faltas puedo tener antes de perder la plaza?", None),  # rules, not records
    ("¿Cuántas faltas y entregas vencidas hay?", None),  # two topics: no guessing
    ("¿Qué es la asistencia online?", None),  # no figures asked
])
def test_routing_rules(question, topic):
    assert records.topic_of(question) == topic


def test_coder_record_question_stays_in_documents(client):
    response = ask(client, login(client, CODER), ATTENDANCE_QUESTION)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["source_kind"] == "documents" and body["record"] is None


def test_e2e_two_cohorts_absent_justified_and_no_sessions(client, db, monkeypatch):
    monkeypatch.setattr(settings, "min_group_size", 1)
    teacher = login(client, DOCENTE)
    enrollments = list(db.scalars(select(Enrollment.id).where(Enrollment.cohort_id == COHORT, Enrollment.estado == "activa")
                                  .order_by(Enrollment.created_at, Enrollment.id)))
    assert len(enrollments) >= 3, "the base seed needs three active enrollments in COH-IA"
    session = client.post(f"/api/v1/cohorts/{COHORT}/attendance-sessions", headers=teacher,
                          json={"session_date": (utcnow().date() - timedelta(days=2)).isoformat(), "shift": "completa"})
    assert session.status_code == 201, session.text
    marks = [{"status": "presente", "modality": "presencial"},
             {"status": "ausente", "justification": "no_justificada"},
             {"status": "ausente", "justification": "justificada"}]
    for enrollment_id, mark in zip(enrollments, marks):
        put = client.put(f"/api/v1/attendance-sessions/{session.json()['id']}/records/{enrollment_id}", headers=teacher, json=mark)
        assert put.status_code == 200, put.text

    body = ask(client, teacher, ATTENDANCE_QUESTION, COHORT).json()
    assert body["status"] == "answered" and body["source_kind"] == "records" and body["mode"] == "template"
    assert body["retrieval"] is None and body["citations"] == []
    assert body["record"]["tool"] == "get_attendance_summary" and body["record"]["aggregate_only"] is False
    assert body["record"]["source"] and body["record"]["rule"] and body["record"]["generated_at"]
    for fragment in ("asistidos 1 ", "falta justificada 1,", "falta no justificada 1,", "33,3 %"):
        assert fragment in body["answer"], (fragment, body["answer"])

    empty = ask(client, teacher, ATTENDANCE_QUESTION, OTHER).json()
    assert empty["status"] == "no_source" and empty["source_kind"] == "records"
    assert empty["answer"].startswith(f"No hay registros de asistencia en {OTHER}")

    choose = ask(client, teacher, ATTENDANCE_QUESTION).json()
    assert choose["status"] == "no_source" and choose["answer"] == CHOOSE_COHORT
    assert set(choose["scope_cohorts"]) == {COHORT, OTHER}

    events = list(db.scalars(select(AuditEvent).where(AuditEvent.action == "assistant.ask")))
    assert len(events) == 3
    assert {e.meta["result"] for e in events} == {"answered", "no_source"}
    assert all(e.meta["source_kind"] == "records" for e in events)
    assert all(ATTENDANCE_QUESTION not in json.dumps(e.meta, ensure_ascii=False) for e in events)


def test_coordination_gets_totals_only(client, monkeypatch):
    monkeypatch.setattr(settings, "min_group_size", 1)
    body = ask(client, login(client, COORD), ATTENDANCE_QUESTION, COHORT).json()
    assert body["source_kind"] == "records", body
    assert body["record"]["aggregate_only"] is True


@pytest.mark.parametrize("question,tool", [
    ("¿Quién tiene entregas vencidas?", "get_pending_submissions"),
    ("¿Cuántos coders hay en cada nivel de competencias?", "get_competency_progress"),
])
def test_submissions_and_competencies_route_to_their_tools(client, db, question, tool):
    load_academic(db, load_seed())
    response = ask(client, login(client, DOCENTE), question, COHORT)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "answered" and body["record"]["tool"] == tool
    enrollment_ids = db.scalars(select(Enrollment.id).where(Enrollment.cohort_id == COHORT))
    assert not any(str(e) in response.text for e in enrollment_ids)  # totals only, nobody singled out


def test_ask_contract_keeps_new_fields_optional():
    schema = app.openapi()["components"]["schemas"]["AskOut"]
    assert {"source_kind", "record"} <= set(schema["properties"])
    assert not {"source_kind", "record"} & set(schema["required"])
