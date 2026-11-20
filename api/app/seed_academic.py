"""KAN-173 (seed v2): academic synthetic data for the API, derived from the shared seed.json.

It follows the rules of the web prototype's migration (src/gistar/migrate.ts) so the local web and the API tell the
same story: each program's competency catalogue becomes one published framework pinned to its cohorts; legacy levels
become dated assessments (plus the synthetic sprint 1); attendance counters become half-day sessions and records with
the same absence pattern. The #67 model also needs every absence to be justified or not: that split uses the
latent-risk parameters of the dropout generator (ml/dropout/data.py), so a coder who misses more sessions has a higher
share of unjustified absences. Deterministic (fixed seed). Loaded once: skipped when a competency framework exists.
If migrate.ts changes these rules, change them here too; tests/test_seed_academic.py checks the totals.
"""

from __future__ import annotations

import random
import uuid
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.attendance.models import AttendanceRecord, AttendanceRecordRevision, AttendanceSession
from app.modules.catalog.models import Cohort
from app.modules.competencies.models import CohortCompetencyFramework, Competency, CompetencyAssessment, CompetencyFramework
from app.modules.identity.models import Person, User
from app.modules.learning.models import Enrollment

SEED = 173
MADRID = ZoneInfo("Europe/Madrid")
TEACHER_EMAIL = "docente@gistar.example"

# Same constants as src/gistar/migrate.ts.
LEGACY_CUTOFF = date(2026, 10, 30)
HOLIDAYS = {date(2026, 10, 12), date(2026, 11, 1), date(2026, 12, 8)}
LEGACY_EVIDENCE = "Valor heredado del modelo v1 (sin fecha original)."
SPRINT_EVIDENCE = "Revisión sintética del sprint 1"
SPRINTS = (  # cohort, review date, competencies of the rubric criteria
    ("COH-IA", date(2026, 10, 20), ("IA-01", "IA-03", "IA-07")),
    ("COH-DATA", date(2026, 10, 27), ("DAT-02", "DAT-03", "DAT-07")),
)
SPRINT_MISSING = {"E-019"}
SPRINT_UNREVIEWED = {"E-002", "E-006", "E-013", "E-017"}

# Latent-risk parameters of ml/dropout/data.py: per session 10 % unknown, 10 % justified,
# and 8 % + 35 % x latent unjustified.
JUSTIFIED_SHARE = 0.10
UNJUSTIFIED_BASE = 0.08
UNJUSTIFIED_PER_LATENT = 0.35


@dataclass(frozen=True)
class SessionPlan:
    weekdays: tuple[int, ...]  # 0 = Monday, as weekday() in src/gistar/dates.ts
    start: time
    end: time
    shift: str  # 4-hour sessions are half days (0.5) in the #67 model


SESSION_PLAN = {
    "COH-IA": SessionPlan((0, 3), time(9, 30), time(13, 30), "manana"),
    "COH-DATA": SessionPlan((1, 4), time(15, 30), time(19, 30), "tarde"),
}
DEFAULT_PLAN = SessionPlan((0, 2), time(10, 0), time(14, 0), "manana")


def load_academic(db: Session, data: dict) -> dict[str, int] | None:
    """Loads frameworks, assessments and attendance once. Returns the counts, or None when already present."""
    if db.scalar(select(CompetencyFramework.id).limit(1)) is not None:
        return None
    teacher = db.scalar(select(User).where(User.email == TEACHER_EMAIL))
    if teacher is None:
        raise RuntimeError("The academic seed needs the base seed first (teacher account not found)")
    cohorts = sorted(db.scalars(select(Cohort)), key=lambda c: c.id)
    enrollments = {
        ref: enrollment
        for ref, enrollment in db.execute(select(Person.legacy_ref, Enrollment).join(Enrollment, Enrollment.person_id == Person.id))
    }
    competencies, frameworks = _frameworks(db, data, cohorts, teacher)
    assessments = _assessments(db, data, competencies, enrollments, teacher)
    sessions, records = _attendance(db, data, cohorts, enrollments, teacher)
    db.commit()
    return {"frameworks": frameworks, "assessments": assessments, "sessions": sessions, "records": records}


def _frameworks(db: Session, data: dict, cohorts: list[Cohort], teacher: User) -> tuple[dict[str, Competency], int]:
    by_program: dict[str, list[dict]] = {}
    for item in data["competencias"]:
        by_program.setdefault(item["programa_id"], []).append(item)
    competencies: dict[str, Competency] = {}
    for program_id, items in sorted(by_program.items()):
        starts = [c.inicio for c in cohorts if c.program_id == program_id]
        published_at = datetime.combine(min(starts) if starts else LEGACY_CUTOFF, time(9), MADRID)
        framework = CompetencyFramework(program_id=program_id, version=1, estado="borrador", created_by=teacher.id, created_at=published_at)
        db.add(framework)
        db.flush()
        for order, item in enumerate(items, start=1):
            competency = Competency(
                framework_id=framework.id, codigo=item["codigo"], nombre=item["nombre"],
                descripcion=item.get("descripcion") or f"Competencia «{item['nombre']}» del catálogo del programa (descripción sintética).",
                level_1=_level(item, "1"), level_2=_level(item, "2"), level_3=_level(item, "3"), orden=item.get("orden", order),
            )
            db.add(competency)
            competencies[item["id"]] = competency
        db.flush()  # insert while still a draft: the frozen-competency trigger rejects changes to published trees
        framework.estado, framework.published_at = "publicada", published_at
        for cohort in cohorts:
            if cohort.program_id == program_id:
                db.add(CohortCompetencyFramework(cohort_id=cohort.id, framework_id=framework.id, assigned_by=teacher.id, assigned_at=published_at))
    db.flush()
    return competencies, len(by_program)


def _level(item: dict, key: str) -> str:
    levels = item.get("niveles") or {}
    return levels.get(key) or levels.get(int(key)) or ""


def _sprint_level(legacy: int | None) -> int | None:
    if legacy is None:
        return None
    return legacy - 1 if legacy >= 2 else 1


def _assessments(db: Session, data: dict, competencies: dict[str, Competency], enrollments: dict, teacher: User) -> int:
    legacy = {(e["coder_id"], e["competencia_id"]): e["nivel_validado"] for e in data["evaluaciones_competencia"]}
    rows = []
    for cohort_id, reviewed, competency_ids in SPRINTS:
        for coder in data["coders"]:
            if coder["cohorte_id"] != cohort_id or coder["id"] in SPRINT_MISSING | SPRINT_UNREVIEWED:
                continue
            for competency_id in competency_ids:
                level = _sprint_level(legacy.get((coder["id"], competency_id)))
                if level is not None:
                    rows.append((coder["id"], competency_id, level, reviewed, SPRINT_EVIDENCE))
    for (coder_id, competency_id), level in legacy.items():
        if level:  # None means "sin evaluar", never level 0
            rows.append((coder_id, competency_id, level, LEGACY_CUTOFF, LEGACY_EVIDENCE))
    count = 0
    for coder_id, competency_id, level, day, evidence in rows:
        enrollment, competency = enrollments.get(coder_id), competencies.get(competency_id)
        if enrollment is None or competency is None:
            continue
        db.add(CompetencyAssessment(
            enrollment_id=enrollment.id, competency_id=competency.id, level=level, evidence=evidence,
            assessed_by=teacher.id, assessed_at=datetime.combine(day, time(18), MADRID),
        ))
        count += 1
    db.flush()
    return count


def _attendance(db: Session, data: dict, cohorts: list[Cohort], enrollments: dict, teacher: User) -> tuple[int, int]:
    simulated_now = datetime.fromisoformat(f"{data['meta']['fecha_simulada']}T12:00")  # wall clock, as in migrate.ts
    summaries = {s["coder_id"]: s for s in data["asistencias_resumen"]}
    coder_cohort = {c["id"]: c["cohorte_id"] for c in data["coders"]}
    session_count = record_count = 0
    for cohort in cohorts:
        plan = SESSION_PLAN.get(cohort.id, DEFAULT_PLAN)
        days = [d for d in _days(cohort.inicio, cohort.fin) if d.weekday() in plan.weekdays and d not in HOLIDAYS]
        sessions = [
            AttendanceSession(cohort_id=cohort.id, session_date=day, shift=plan.shift, duration_fraction=Decimal("0.5"),
                              created_by=teacher.id, created_at=datetime.combine(cohort.inicio, time(8), MADRID))
            for day in days
        ]
        db.add_all(sessions)
        db.flush()
        session_count += len(sessions)
        past = [s for s in sessions if datetime.combine(s.session_date, plan.start) <= simulated_now]
        cohort_summaries = [summaries[c] for c in sorted(summaries) if coder_cohort.get(c) == cohort.id]
        inherited = min(len(past), max((s["sesiones_totales"] for s in cohort_summaries), default=0))
        for summary in cohort_summaries:
            enrollment = enrollments.get(summary["coder_id"])
            if enrollment is None:
                continue
            total = min(summary["sesiones_totales"], inherited)
            absent = _absent_indexes(total, summary["faltas"])
            rng = random.Random(f"{SEED}:{summary['coder_id']}")
            unjustified = _unjustified_probability(summary)
            for index in range(total):
                session = past[index]
                if index in absent:
                    values = ("ausente", None, "no_justificada" if rng.random() < unjustified else "justificada")
                else:
                    values = ("presente", "presencial", None)
                _record(db, session, enrollment, values, teacher, datetime.combine(session.session_date, plan.end, MADRID))
                record_count += 1
    db.flush()
    return session_count, record_count


def _days(start: date, end: date) -> list[date]:
    return [start + timedelta(days=n) for n in range((end - start).days + 1)]


def _absent_indexes(total: int, absences: int) -> set[int]:
    """Same pattern as migrate.ts: the latest sessions first, every other one."""
    absent: set[int] = set()
    index = total - 1
    for k in range(min(absences, total)):
        absent.add(index if index >= 0 else total - 1 - k)
        index -= 2
    return absent


def _unjustified_probability(summary: dict) -> float:
    """Latent risk estimated from the absence rate, then the dropout generator's unjustified vs justified split."""
    rate = summary["faltas"] / summary["sesiones_totales"] if summary["sesiones_totales"] else 0.0
    latent = min(1.0, max(0.0, (rate - UNJUSTIFIED_BASE) / UNJUSTIFIED_PER_LATENT))
    unjustified = UNJUSTIFIED_BASE + UNJUSTIFIED_PER_LATENT * latent
    return unjustified / (unjustified + JUSTIFIED_SHARE)


def _record(db: Session, session: AttendanceSession, enrollment: Enrollment, values: tuple, teacher: User, when: datetime) -> None:
    status, modality, justification = values
    record = AttendanceRecord(
        id=uuid.uuid4(), session_id=session.id, enrollment_id=enrollment.id, status=status, modality=modality,
        justification=justification, version=1, recorded_by=teacher.id, updated_at=when,
    )
    db.add(record)
    db.add(AttendanceRecordRevision(
        record_id=record.id, version=1, status=status, modality=modality, justification=justification,
        reason=None, changed_by=teacher.id, changed_at=when,
    ))
