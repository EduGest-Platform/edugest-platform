"""KAN-207: two active tokens lose a revoked cohort in attendance and competencies immediately."""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.db import SessionLocal, utcnow
from app.main import app
from app.modules.attendance.models import AttendanceRecord, AttendanceRecordRevision
from app.modules.catalog.models import Cohort
from app.modules.competencies.models import CompetencyAssessment
from app.modules.identity.models import RoleAssignment, User
from app.modules.learning.models import Enrollment
from tests.conftest import ADMIN, DOCENTE, login

COHORTS = ("COH-IA", "COH-DATA")


@pytest.fixture
def academic_cases(client, db):
    teacher = login(client, DOCENTE)
    today = utcnow().date()
    result = {}
    for cohort_id in COHORTS:
        cohort = db.get(Cohort, cohort_id)
        cohort.inicio, cohort.fin = today - timedelta(days=10), today + timedelta(days=10)
        db.commit()
        enrollment = db.scalar(select(Enrollment).where(Enrollment.cohort_id == cohort_id, Enrollment.estado == "activa"))
        assert enrollment is not None
        session = client.post(f"/api/v1/cohorts/{cohort_id}/attendance-sessions", headers=teacher,
                              json={"session_date": (today - timedelta(days=2)).isoformat(), "shift": "completa"})
        assert session.status_code == 201, session.text
        session_id = session.json()["id"]
        record = client.put(f"/api/v1/attendance-sessions/{session_id}/records/{enrollment.id}", headers=teacher,
                            json={"status": "presente", "modality": "presencial"})
        assert record.status_code == 200, record.text
        tree = client.post(f"/api/v1/programs/{cohort.program_id}/competency-frameworks", headers=teacher,
                           json={"competencies": [{"codigo": "C1", "nombre": "Synthetic scope competency",
                                   "level_1": "Synthetic assisted", "level_2": "Synthetic independent", "level_3": "Synthetic explanation"}]})
        assert tree.status_code == 201, tree.text
        published = client.post(f"/api/v1/competency-frameworks/{tree.json()['id']}/publish", headers=teacher)
        assert published.status_code == 200
        framework = published.json()
        assigned = client.put(f"/api/v1/cohorts/{cohort_id}/competency-framework", headers=teacher,
                              json={"framework_id": framework["id"]})
        assert assigned.status_code == 200
        competency_id = framework["competencies"][0]["id"]
        assessment = client.post(f"/api/v1/enrollments/{enrollment.id}/assessments", headers=teacher,
                                 json={"competency_id": competency_id, "level": 1, "evidence": "Synthetic original assessment"})
        assert assessment.status_code == 201, assessment.text
        result[cohort_id] = {"enrollment": str(enrollment.id), "session": session_id,
                             "record": record.json()["id"], "competency": competency_id}
    return result


def read_paths(cohort, case):
    return (f"/api/v1/cohorts/{cohort}/attendance-sessions",
            f"/api/v1/cohorts/{cohort}/attendance-summary?enrollment_id={case['enrollment']}",
            f"/api/v1/attendance-records/{case['record']}/revisions",
            f"/api/v1/cohorts/{cohort}/competencies",
            f"/api/v1/enrollments/{case['enrollment']}/assessments")


def counts(db):
    return tuple(db.scalar(select(func.count()).select_from(model))
                 for model in (AttendanceRecord, AttendanceRecordRevision, CompetencyAssessment))


@pytest.mark.parametrize("revoked_cohort", COHORTS)
def test_revoking_one_cohort_blocks_both_tokens_without_erasing_or_widening_access(client, db, academic_cases, revoked_cohort):
    other_cohort = next(cohort for cohort in COHORTS if cohort != revoked_cohort)
    revoked = academic_cases[revoked_cohort]
    with TestClient(app) as second:
        tokens = ((client, login(client, DOCENTE)), (second, login(second, DOCENTE)))
        admin = login(client, ADMIN)
        paths = [path for cohort, case in academic_cases.items() for path in read_paths(cohort, case)]
        baseline = {path: client.get(path, headers=admin).json() for path in paths}
        for browser, token in tokens:
            assert all(browser.get(path, headers=token).status_code == 200 for path in paths)
        user_id = db.scalar(select(User.id).where(User.email == DOCENTE))
        assignment = db.scalar(select(RoleAssignment).where(RoleAssignment.user_id == user_id,
                                                            RoleAssignment.role == "docente",
                                                            RoleAssignment.scope_type == "cohort",
                                                            RoleAssignment.scope_id == revoked_cohort,
                                                            RoleAssignment.revoked_at.is_(None)))
        assert assignment is not None
        assignment.revoked_at = utcnow()
        db.commit()
        before = counts(db)
        for browser, token in tokens:
            # Session authentication remains valid; current assignments determine every action.
            assert browser.get("/api/v1/auth/me", headers=token).status_code == 200
            for path in read_paths(revoked_cohort, revoked):
                assert browser.get(path, headers=token).status_code == 403, path
            for path in read_paths(other_cohort, academic_cases[other_cohort]):
                assert browser.get(path, headers=token).status_code == 200, path
            correction = browser.put(f"/api/v1/attendance-sessions/{revoked['session']}/records/{revoked['enrollment']}",
                                     headers=token, json={"status": "ausente", "justification": "no_justificada",
                                                          "reason": "Synthetic forbidden correction"})
            assert correction.status_code == 403
            assessment = browser.post(f"/api/v1/enrollments/{revoked['enrollment']}/assessments", headers=token,
                                       json={"competency_id": revoked["competency"], "level": 2,
                                             "evidence": "Synthetic forbidden assessment"})
            assert assessment.status_code == 403
        with SessionLocal() as verification:
            assert counts(verification) == before
        assert {path: client.get(path, headers=admin).json() for path in paths} == baseline
