"""KAN-173 (seed v2): academic data derived from seed.json with the web prototype's rules."""

from collections import Counter
from decimal import Decimal

import pytest
from sqlalchemy import func, select, text

from app.modules.admissions.models import Application
from app.modules.attendance.models import AttendanceRecord, AttendanceSession
from app.modules.competencies.models import CohortCompetencyFramework, Competency, CompetencyAssessment, CompetencyFramework
from app.modules.identity.models import Person, User
from app.modules.learning.models import Enrollment
from app.seed import load_seed
from app.seed_academic import load_academic

ACADEMIC = "competency_assessment, cohort_competency_framework, competency, competency_framework, " \
           "attendance_record_revision, attendance_record, attendance_session"


@pytest.fixture
def data():
    return load_seed()


@pytest.fixture
def loaded(db, data):
    db.execute(text(f"TRUNCATE {ACADEMIC} CASCADE"))
    db.commit()
    return load_academic(db, data)


def by_coder(db, model):
    rows = db.execute(select(Person.legacy_ref, model).join(Enrollment, Enrollment.person_id == Person.id)
                      .join(model, model.enrollment_id == Enrollment.id)).all()
    return rows


def test_at_least_100_applications_with_synthetic_emails(db):
    assert db.scalar(select(func.count()).select_from(Application)) >= 100
    domains = {email.rsplit("@", 1)[-1] for email in db.scalars(select(Person.email)) if email}
    assert domains <= {"gistar.example", "example.test"}, f"dominios no sintéticos: {domains}"


def test_one_published_framework_per_program_pinned_to_its_cohorts(db, data, loaded):
    frameworks = list(db.scalars(select(CompetencyFramework)))
    assert loaded["frameworks"] == len(frameworks) == 2
    assert all(f.estado == "publicada" and f.version == 1 and f.published_at for f in frameworks)
    expected = Counter(c["programa_id"] for c in data["competencias"])
    for framework in frameworks:
        assert db.scalar(select(func.count()).select_from(Competency).where(Competency.framework_id == framework.id)) == expected[framework.program_id]
    assert db.scalar(select(func.count()).select_from(CohortCompetencyFramework)) == len(data["cohortes"])


def test_current_level_is_the_legacy_level_and_never_zero(db, data, loaded):
    competencies = {c.id: c.codigo for c in db.scalars(select(Competency))}
    latest = {}
    for ref, assessment in sorted(by_coder(db, CompetencyAssessment), key=lambda row: row[1].assessed_at):
        latest[(ref, assessment.competency_id)] = assessment.level
    codes = {c["id"]: c["codigo"] for c in data["competencias"]}
    current = {(ref, competencies[cid]): level for (ref, cid), level in latest.items()}
    for item in data["evaluaciones_competencia"]:
        assert current.get((item["coder_id"], codes[item["competencia_id"]])) == item["nivel_validado"]
    assert all(1 <= level <= 3 for level in current.values())


def test_attendance_matches_the_counters_and_every_absence_is_classified(db, data, loaded):
    counts = Counter()
    for ref, record in by_coder(db, AttendanceRecord):
        counts[(ref, record.status)] += 1
        if record.status == "ausente":
            assert record.justification in ("justificada", "no_justificada") and record.modality is None
        else:
            assert record.modality == "presencial" and record.justification is None
    for summary in data["asistencias_resumen"]:
        assert counts[(summary["coder_id"], "presente")] == summary["presencias"]
        assert counts[(summary["coder_id"], "ausente")] == summary["faltas"]
    fractions = set(db.scalars(select(AttendanceSession.duration_fraction)))
    assert {float(f) for f in fractions} == {0.5}
    assert loaded["records"] == sum(counts.values())


def test_loading_twice_changes_nothing(db, data, loaded):
    before = db.scalar(select(func.count()).select_from(AttendanceRecord))
    again = load_academic(db, data)
    assert not any(again.values()), again
    assert db.scalar(select(func.count()).select_from(AttendanceRecord)) == before


def test_same_seed_gives_the_same_data(db, data, loaded):
    def snapshot():
        return sorted(
            (ref, record.status, record.justification, str(session.session_date))
            for ref, record, session in db.execute(
                select(Person.legacy_ref, AttendanceRecord, AttendanceSession)
                .join(Enrollment, Enrollment.person_id == Person.id)
                .join(AttendanceRecord, AttendanceRecord.enrollment_id == Enrollment.id)
                .join(AttendanceSession, AttendanceSession.id == AttendanceRecord.session_id)
            )
        )
    first = snapshot()
    db.execute(text(f"TRUNCATE {ACADEMIC} CASCADE"))
    db.commit()
    load_academic(db, data)
    assert snapshot() == first


def teacher_id(db):
    return db.scalar(select(User.id).where(User.email == "docente@gistar.example"))


def count(db, model, *where):
    return db.scalar(select(func.count()).select_from(model).where(*where))


def test_a_draft_created_through_the_api_does_not_block_the_load(db, data):
    db.execute(text(f"TRUNCATE {ACADEMIC} CASCADE"))
    draft = CompetencyFramework(program_id="P-IA", version=1, estado="borrador", created_by=teacher_id(db))
    db.add(draft)
    db.flush()
    db.add(Competency(framework_id=draft.id, codigo="C1", nombre="Borrador manual", level_1="a", level_2="b", level_3="c", orden=1))
    db.commit()
    draft_id = draft.id
    created = load_academic(db, data)
    assert created["frameworks"] == 2 and created["records"] > 0
    kept = db.get(CompetencyFramework, draft_id)
    assert kept.estado == "borrador" and count(db, Competency, Competency.framework_id == draft_id) == 1
    published = db.scalar(select(CompetencyFramework).where(CompetencyFramework.program_id == "P-IA",
                                                            CompetencyFramework.estado == "publicada"))
    assert published.version == 2
    pins = dict(db.execute(select(CohortCompetencyFramework.cohort_id, CohortCompetencyFramework.framework_id)).all())
    assert set(pins) == {c["id"] for c in data["cohortes"]} and pins["COH-IA"] == published.id
    with_records = set(db.scalars(select(AttendanceSession.cohort_id)
                                  .join(AttendanceRecord, AttendanceRecord.session_id == AttendanceSession.id)))
    assert {"COH-IA", "COH-DATA"} <= with_records


def test_a_session_created_through_the_api_is_reused_without_touching_its_record(db, data, loaded):
    session, record = db.execute(
        select(AttendanceSession, AttendanceRecord).join(AttendanceRecord, AttendanceRecord.session_id == AttendanceSession.id)
        .where(AttendanceSession.cohort_id == "COH-IA")
        .order_by(AttendanceSession.session_date, AttendanceRecord.enrollment_id).limit(1)
    ).one()
    day, shift, enrollment_id = session.session_date, session.shift, record.enrollment_id
    clean_sessions, clean_records = count(db, AttendanceSession), loaded["records"]
    db.execute(text(f"TRUNCATE {ACADEMIC} CASCADE"))
    db.commit()
    manual = AttendanceSession(cohort_id="COH-IA", session_date=day, shift=shift, duration_fraction=Decimal("0.5"),
                               created_by=teacher_id(db))
    db.add(manual)
    db.flush()
    db.add(AttendanceRecord(session_id=manual.id, enrollment_id=enrollment_id, status="retraso", modality="online",
                            justification=None, version=1, recorded_by=teacher_id(db)))
    db.commit()
    manual_id = manual.id
    created = load_academic(db, data)  # no framework yet, so the old guard let this collide on the unique slot
    assert created["sessions"] == clean_sessions - 1 and count(db, AttendanceSession) == clean_sessions
    assert created["records"] == clean_records - 1
    kept = db.scalar(select(AttendanceRecord).where(AttendanceRecord.session_id == manual_id,
                                                    AttendanceRecord.enrollment_id == enrollment_id))
    assert (kept.status, kept.modality, kept.version) == ("retraso", "online", 1)
    assert count(db, AttendanceRecord, AttendanceRecord.session_id == manual_id) > 1
