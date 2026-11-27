"""KAN-57: versioned competency tree per bootcamp, level 1–3 assessments with assessor/date, no cross-course leakage."""

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError

from app.modules.audit.models import AuditEvent
from app.modules.competencies.models import CohortCompetencyFramework, CompetencyAssessment
from app.modules.identity.models import RoleAssignment, User
from app.modules.learning.models import Enrollment
from tests.conftest import CAPT_IA, CODER, COORD, DOCENTE, login

PROGRAM, COHORT = "P-IA", "COH-IA"
OTHER_PROGRAM, OTHER_COHORT = "P-DATA", "COH-DATA"


def tree(*codes: str) -> dict:
    return {
        "competencies": [
            {"codigo": c, "nombre": f"Competencia {c}", "level_1": "Lo hace con ayuda", "level_2": "Lo hace solo", "level_3": "Lo explica a otros"}
            for c in codes
        ]
    }


@pytest.fixture
def teacher(client):
    return login(client, DOCENTE)


def published_tree(client, headers, program=PROGRAM, codes=("C1", "C2", "C3")) -> dict:
    draft = client.post(f"/api/v1/programs/{program}/competency-frameworks", json=tree(*codes), headers=headers)
    assert draft.status_code == 201, draft.text
    published = client.post(f"/api/v1/competency-frameworks/{draft.json()['id']}/publish", headers=headers)
    assert published.status_code == 200, published.text
    return published.json()


def assign(client, headers, framework_id, cohort=COHORT):
    return client.put(f"/api/v1/cohorts/{cohort}/competency-framework", json={"framework_id": framework_id}, headers=headers)


def enrollment_of(db, cohort_id=COHORT) -> str:
    return str(db.scalar(select(Enrollment.id).where(Enrollment.cohort_id == cohort_id).order_by(Enrollment.created_at, Enrollment.id)))


def assess(client, headers, enrollment, competency_id, level, evidence="Entrega del proyecto 1"):
    return client.post(f"/api/v1/enrollments/{enrollment}/assessments", json={"competency_id": competency_id, "level": level, "evidence": evidence}, headers=headers)


# ---------- Framework versions ----------


def test_teacher_creates_edits_and_publishes_a_tree(client, teacher):
    draft = client.post(f"/api/v1/programs/{PROGRAM}/competency-frameworks", json=tree("C1"), headers=teacher).json()
    assert draft["version"] == 1 and draft["estado"] == "borrador"
    edited = client.put(f"/api/v1/competency-frameworks/{draft['id']}/competencies", json=tree("C1", "C2"), headers=teacher).json()
    assert [c["codigo"] for c in edited["competencies"]] == ["C1", "C2"]
    published = client.post(f"/api/v1/competency-frameworks/{draft['id']}/publish", headers=teacher).json()
    assert published["estado"] == "publicada" and published["published_at"]


def test_published_tree_is_frozen_and_new_version_archives_the_old_one(client, teacher):
    v1 = published_tree(client, teacher)
    edit = client.put(f"/api/v1/competency-frameworks/{v1['id']}/competencies", json=tree("C9"), headers=teacher)
    assert edit.status_code == 409 and edit.json()["code"] == "framework_not_draft"
    v2 = published_tree(client, teacher, codes=("C1", "C2"))
    versions = client.get(f"/api/v1/programs/{PROGRAM}/competency-frameworks", headers=teacher).json()["items"]
    assert [(v["version"], v["estado"]) for v in versions] == [(1, "archivada"), (2, "publicada")]
    assert v2["version"] == 2 and len(versions[0]["competencies"]) == 3  # old version still readable


def test_database_freezes_competencies_of_a_published_tree(client, db, teacher):
    v1 = published_tree(client, teacher)
    with pytest.raises(DBAPIError):
        db.execute(text("UPDATE competency SET nombre = 'Cambiada' WHERE framework_id = :id"), {"id": v1["id"]})
    db.rollback()


@pytest.mark.parametrize("body", [tree("C1", "C1"), tree("X1"), tree("C0"), {"competencies": []}])
def test_invalid_trees_are_rejected(client, teacher, body):
    assert client.post(f"/api/v1/programs/{PROGRAM}/competency-frameworks", json=body, headers=teacher).status_code == 422


# ---------- Cohort assignment: no inheritance across courses ----------


def test_cohort_cannot_use_another_programs_tree(client, teacher):
    data_tree = published_tree(client, teacher, program=OTHER_PROGRAM)
    r = assign(client, teacher, data_tree["id"])
    assert r.status_code == 409 and r.json()["code"] == "framework_other_program"


def test_cohort_cannot_use_a_draft(client, teacher):
    draft = client.post(f"/api/v1/programs/{PROGRAM}/competency-frameworks", json=tree("C1"), headers=teacher).json()
    assert assign(client, teacher, draft["id"]).json()["code"] == "framework_not_published"


def test_cohort_without_tree_has_no_competencies(client, teacher):
    assert client.get(f"/api/v1/cohorts/{COHORT}/competencies", headers=teacher).json()["framework"] is None


def test_competency_of_another_course_cannot_be_assessed(client, db, teacher):
    ia = published_tree(client, teacher)
    data = published_tree(client, teacher, program=OTHER_PROGRAM)
    assign(client, teacher, ia["id"])
    r = assess(client, teacher, enrollment_of(db), data["competencies"][0]["id"], 2)
    assert r.status_code == 409 and r.json()["code"] == "competency_not_in_cohort"


# ---------- Assessments ----------


def test_levels_show_assessor_date_and_latest_wins_without_losing_history(client, db, teacher):
    framework = published_tree(client, teacher)
    assign(client, teacher, framework["id"])
    enrollment, c1 = enrollment_of(db), framework["competencies"][0]["id"]
    assert assess(client, teacher, enrollment, c1, 1).status_code == 201
    second = assess(client, teacher, enrollment, c1, 3, evidence="Proyecto final")
    assert second.json()["assessed_by"] == "Docente demo" and second.json()["framework_version"] == 1
    result = client.get(f"/api/v1/enrollments/{enrollment}/assessments", headers=teacher).json()
    current = {c["codigo"]: c["level"] for c in result["current"]}
    assert current == {"C1": 3, "C2": None, "C3": None}  # not assessed = null, never level 0
    assert [h["level"] for h in result["history"]] == [1, 3]


def test_old_assessments_stay_traceable_after_a_new_version(client, db, teacher):
    v1 = published_tree(client, teacher)
    assign(client, teacher, v1["id"])
    enrollment = enrollment_of(db)
    assess(client, teacher, enrollment, v1["competencies"][0]["id"], 2)
    v2 = published_tree(client, teacher, codes=("C1", "C4"))
    assert assign(client, teacher, v2["id"]).status_code == 200
    result = client.get(f"/api/v1/enrollments/{enrollment}/assessments", headers=teacher).json()
    assert result["framework_version"] == 2
    assert {c["codigo"]: c["level"] for c in result["current"]} == {"C1": None, "C4": None}
    assert [(h["codigo"], h["framework_version"], h["level"]) for h in result["history"]] == [("C1", 1, 2)]


@pytest.mark.parametrize("level", [0, 4])
def test_level_must_be_between_1_and_3(client, db, teacher, level):
    framework = published_tree(client, teacher)
    assign(client, teacher, framework["id"])
    assert assess(client, teacher, enrollment_of(db), framework["competencies"][0]["id"], level).status_code == 422


def test_assessments_cannot_be_edited_or_deleted(client, db, teacher):
    framework = published_tree(client, teacher)
    assign(client, teacher, framework["id"])
    assess(client, teacher, enrollment_of(db), framework["competencies"][0]["id"], 2)
    assessment_id = db.scalar(select(CompetencyAssessment.id))
    for statement in ("UPDATE competency_assessment SET level = 3 WHERE id = :id", "DELETE FROM competency_assessment WHERE id = :id"):
        with pytest.raises(DBAPIError):
            db.execute(text(statement), {"id": assessment_id})
        db.rollback()


# ---------- Permissions ----------


def test_teacher_of_another_cohort_gets_403(client, db):
    teacher = login(client, DOCENTE)
    framework = published_tree(client, teacher)
    assign(client, teacher, framework["id"])
    teacher_id = db.scalar(select(User.id).where(User.email == DOCENTE))
    db.query(RoleAssignment).filter(RoleAssignment.user_id == teacher_id, RoleAssignment.scope_id == COHORT).delete()
    db.commit()
    headers = login(client, DOCENTE)  # now only teaches COH-DATA
    assert assess(client, headers, enrollment_of(db), framework["competencies"][0]["id"], 2).status_code == 403
    assert client.get(f"/api/v1/cohorts/{COHORT}/competencies", headers=headers).status_code == 403
    assert client.post(f"/api/v1/programs/{PROGRAM}/competency-frameworks", json=tree("C1"), headers=headers).status_code == 403


@pytest.mark.parametrize("email", [CAPT_IA, COORD, CODER])
def test_non_teaching_roles_cannot_configure_or_assess(client, email):
    headers = login(client, email)
    assert client.post(f"/api/v1/programs/{PROGRAM}/competency-frameworks", json=tree("C1"), headers=headers).status_code == 403
    assert client.get(f"/api/v1/cohorts/{COHORT}/competencies", headers=headers).status_code == 403


def test_assessment_roster_only_shows_the_assigned_cohort(client, db):
    user_id = db.scalar(select(User.id).where(User.email == DOCENTE))
    assignment = db.scalar(select(RoleAssignment).where(
        RoleAssignment.user_id == user_id, RoleAssignment.scope_id == OTHER_COHORT,
    ))
    db.delete(assignment)
    db.commit()
    teacher = login(client, DOCENTE)
    path = f"/api/v1/cohorts/{COHORT}/competency-roster"
    roster = client.get(path, headers=teacher)
    assert roster.status_code == 200
    items = roster.json()["items"]
    assert items and all(set(item) == {"enrollment_id", "display_name"} for item in items)
    assert enrollment_of(db) in {item["enrollment_id"] for item in items}
    assert client.get(f"/api/v1/cohorts/{OTHER_COHORT}/competency-roster", headers=teacher).status_code == 403
    assert client.get(path, headers=login(client, COORD)).status_code == 403
    assert client.get(path).status_code == 401
    missing = client.get("/api/v1/cohorts/COH-MISSING/competency-roster", headers=teacher)
    assert missing.status_code == 404 and missing.json()["code"] == "cohort_not_found"

    included = enrollment_of(db)
    enrollment = db.scalar(select(Enrollment).where(Enrollment.id == included))
    enrollment.estado = "baja_voluntaria"
    db.commit()
    roster = client.get(path, headers=teacher)
    assert roster.status_code == 200
    assert included not in {item["enrollment_id"] for item in roster.json()["items"]}


def test_cohort_activation_is_explicit_scoped_and_audited(client, db, teacher):
    teacher_id = db.scalar(select(User.id).where(User.email == DOCENTE))
    first = published_tree(client, teacher)
    assert db.get(CohortCompetencyFramework, COHORT) is None
    assert assign(client, teacher, first["id"]).status_code == 200
    db.expire_all()
    link = db.get(CohortCompetencyFramework, COHORT)
    assert str(link.framework_id) == first["id"]
    assert link.assigned_by == teacher_id and link.assigned_at is not None

    second = published_tree(client, teacher, codes=("C1", "C4"))
    db.expire_all()
    assert str(db.get(CohortCompetencyFramework, COHORT).framework_id) == first["id"]
    assert assign(client, teacher, second["id"]).status_code == 200
    db.expire_all()
    assert str(db.get(CohortCompetencyFramework, COHORT).framework_id) == second["id"]

    events_query = select(AuditEvent).where(
        AuditEvent.action == "competencies.cohort_framework_assigned",
        AuditEvent.target_id == COHORT,
    ).order_by(AuditEvent.id)
    events = db.scalars(events_query).all()
    assert len(events) == 2
    assert all(event.actor_user_id == teacher_id and event.at is not None for event in events)
    assert events[0].meta["previous"] is None
    assert events[1].meta["previous"] == first["id"]
    assert events[1].meta["framework_id"] == second["id"]

    assert assign(client, login(client, CAPT_IA), second["id"]).status_code == 403
    assert assign(client, {}, second["id"]).status_code == 401
    db.query(RoleAssignment).filter(
        RoleAssignment.user_id == teacher_id, RoleAssignment.scope_id == COHORT,
    ).delete()
    db.commit()
    assert assign(client, login(client, DOCENTE), second["id"]).status_code == 403
    assert assign(client, login(client, DOCENTE), first["id"]).status_code == 403
    db.expire_all()
    assert str(db.get(CohortCompetencyFramework, COHORT).framework_id) == second["id"]
    assert len(db.scalars(events_query).all()) == 2
