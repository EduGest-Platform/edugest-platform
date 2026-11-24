"""KAN-195 / KAN-61 / KAN-62: the assistant answers record questions with the read-only tools (#97), never with SQL.

Routing is deterministic and deliberately narrow. A question goes to records only when:
1. it asks for figures («cuántas», «quién», «resumen», «porcentaje»...),
2. it is about exactly one topic (attendance, submissions or competencies),
3. it is not a question about rules («¿puedo...?», «¿se permite...?», «máximo»...), and
4. the person has staff permission on that topic for the cohort (coders never reach the tools until T21).
Everything else goes to the course documents. In the chat the answer is cohort totals only: no names and no
per-person rows (minimisation). has_data = false becomes «no hay registros», never a zero.
"""

import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Literal
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.authz import Principal
from app.modules.assistant_tools import router as tools
from app.modules.learning.access import cohort_scope, load_cohort

Topic = Literal["attendance", "submissions", "competencies"]

_QUANTITY = re.compile(r"\b(cuant[oa]s?|quien(es)?|que coders|resumen|estado de|porcentaje|tasa)\b")
_RULES = re.compile(r"\b(puedo|pueden?|se permiten?|permitid|maxim|minim|norma|politica|reglamento|obligatori)")
_TOPICS: dict[Topic, re.Pattern[str]] = {
    "attendance": re.compile(r"\b(faltas?|ausencias?|asistencias?|retrasos?)\b"),
    "submissions": re.compile(r"\b(entregas?|entregad[oa]s?|vencidas?)\b"),
    "competencies": re.compile(r"\b(competencias?|nivel(es)?)\b"),
}
_PERMISSIONS: dict[Topic, tuple[str, str]] = {
    "attendance": ("attendance.read", "attendance.aggregate"),
    "submissions": ("submissions.read", "submissions.aggregate"),
    "competencies": ("competencies.read", "competencies.aggregate"),
}
_LABEL: dict[Topic, str] = {"attendance": "asistencia", "submissions": "entregas", "competencies": "competencias"}


@dataclass(frozen=True)
class RecordAnswer:
    tool: str
    source: str
    rule: str
    generated_at: datetime
    aggregate_only: bool
    has_data: bool
    text: str


def _plain(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def topic_of(question: str) -> Topic | None:
    """The single records topic the question asks figures about, or None (then it goes to the documents)."""
    text = _plain(question)
    if not _QUANTITY.search(text) or _RULES.search(text):
        return None
    found = [topic for topic, pattern in _TOPICS.items() if pattern.search(text)]
    return found[0] if len(found) == 1 else None


def record_cohorts(db: Session, p: Principal, topic: Topic, cohort_ids: Iterable[str]) -> list[str]:
    """Cohorts where the person may use the tool for this topic (per-person or totals only)."""
    allowed = []
    for cohort_id in sorted(cohort_ids):
        scope = cohort_scope(load_cohort(db, cohort_id))
        if any(p.can(permission, scope) for permission in _PERMISSIONS[topic]):
            allowed.append(cohort_id)
    return allowed


def _n(value: float | None) -> str:
    return "sin dato" if value is None else f"{value:g}".replace(".", ",")


def _small(min_group_size: int) -> str:
    return (f"El grupo es demasiado pequeño para mostrar totales (mínimo {min_group_size} matrículas). "
            "Es una protección de privacidad, no un cero.")


def _attendance(cohort_id: str, totals) -> str:
    if totals.suppressed:
        return _small(totals.min_group_size)
    rate = "sin dato" if totals.attendance_rate is None else f"{totals.attendance_rate * 100:.1f} %".replace(".", ",")
    return (f"Asistencia en {cohort_id} hasta hoy (en días): asistidos {_n(totals.attended_days)} "
            f"(con retraso {_n(totals.late_days)}), falta justificada {_n(totals.justified_absence_days)}, "
            f"falta no justificada {_n(totals.unjustified_absence_days)}, sin registrar {_n(totals.unrecorded_days)}. "
            f"Tasa de asistencia: {rate}.")


def _submissions(cohort_id: str, data) -> str:
    if data.suppressed:
        return _small(data.min_group_size)
    zone = ZoneInfo(data.timezone)
    parts = [
        f"«{a.title}» (vence el {a.due_at.astimezone(zone):%d/%m/%Y}): a tiempo {a.counts.on_time}, tarde {a.counts.late}, "
        f"pendientes {a.counts.pending}, vencidas {a.counts.overdue}, revisadas {a.counts.reviewed}"
        for a in data.assignments
    ]
    return f"Entregas en {cohort_id} (coders por estado): " + "; ".join(parts) + "."


def _competencies(cohort_id: str, data) -> str:
    if data.suppressed:
        return _small(data.min_group_size)
    parts = [
        f"{d.codigo} {d.nombre}: nivel 1 {d.counts.level_1}, nivel 2 {d.counts.level_2}, nivel 3 {d.counts.level_3}, "
        f"sin evaluar {d.counts.not_assessed}"
        for d in data.distribution
    ]
    return f"Nivel actual en {cohort_id} (árbol v{data.framework_version}, coders por nivel): " + "; ".join(parts) + "."


def answer(db: Session, p: Principal, topic: Topic, cohort_id: str) -> RecordAnswer:
    """Runs the allowlisted tool in-process, with its own permission checks and audit, and words the totals."""
    if topic == "attendance":
        r = tools.tool_attendance_summary(p, db, cohort_id=cohort_id, enrollment_id=None, date_from=None, date_to=None)
        text = _attendance(cohort_id, r.data.cohort_totals) if r.has_data else None
    elif topic == "submissions":
        r = tools.tool_pending_submissions(p, db, cohort_id=cohort_id)
        text = _submissions(cohort_id, r.data) if r.has_data else None
    else:
        r = tools.tool_competency_progress(p, db, cohort_id=cohort_id)
        text = _competencies(cohort_id, r.data) if r.has_data else None
    return RecordAnswer(
        tool=r.tool, source=r.source, rule=r.rule, generated_at=r.generated_at, aggregate_only=r.aggregate_only,
        has_data=r.has_data,
        text=text or f"No hay registros de {_LABEL[topic]} en {cohort_id} para ese periodo. No es un cero: no hay datos.",
    )
