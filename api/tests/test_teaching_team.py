"""Melissa round 3 Q15: the teacher manages its cohort's teaching team; nobody escalates; the last teacher stays."""

import pytest
from sqlalchemy import select

from app.modules.audit.models import AuditEvent
from app.modules.identity.models import RoleAssignment, User
from tests.conftest import CAPT_IA, CODER, COORD, DOCENTE, SEL_IA, login

COHORT, OTHER = "COH-IA", "COH-DATA"


def user_id(db, email) -> str:
    return str(db.scalar(select(User.id).where(User.email == email)))


def team(client, headers, cohort=COHORT):
    return client.get(f"/api/v1/cohorts/{cohort}/teaching-team", headers=headers)


def test_teacher_adds_and_removes_a_colleague_with_audit(client, db):
    teacher = login(client, DOCENTE)
    colleague = user_id(db, SEL_IA)
    added = client.put(f"/api/v1/cohorts/{COHORT}/teaching-team/{colleague}", headers=teacher)
    assert added.status_code == 200, added.text
    assert colleague in {m["user_id"] for m in added.json()["members"]}
    # The new teacher can now record attendance in this cohort only.
    assert client.get(f"/api/v1/cohorts/{COHORT}/attendance-summary", headers=login(client, SEL_IA)).status_code == 200
    removed = client.delete(f"/api/v1/cohorts/{COHORT}/teaching-team/{colleague}", headers=teacher)
    assert removed.status_code == 200 and colleague not in {m["user_id"] for m in removed.json()["members"]}
    actions = set(db.scalars(select(AuditEvent.action).where(AuditEvent.target_id == COHORT)))
    assert {"cohort.teacher_added", "cohort.teacher_removed"} <= actions


def test_re_adding_a_removed_teacher_reactivates_the_same_assignment(client, db):
    teacher = login(client, DOCENTE)
    colleague = user_id(db, SEL_IA)
    for _ in range(2):
        client.put(f"/api/v1/cohorts/{COHORT}/teaching-team/{colleague}", headers=teacher)
        client.delete(f"/api/v1/cohorts/{COHORT}/teaching-team/{colleague}", headers=teacher)
    client.put(f"/api/v1/cohorts/{COHORT}/teaching-team/{colleague}", headers=teacher)
    rows = db.scalars(select(RoleAssignment).where(RoleAssignment.user_id == colleague, RoleAssignment.scope_id == COHORT)).all()
    assert len(rows) == 1 and rows[0].revoked_at is None


def test_the_last_teacher_cannot_be_removed(client, db):
    teacher = login(client, DOCENTE)
    r = client.delete(f"/api/v1/cohorts/{COHORT}/teaching-team/{user_id(db, DOCENTE)}", headers=teacher)
    assert r.status_code == 409 and r.json()["code"] == "last_teacher"


def test_person_accounts_never_join_the_team(client, db):
    r = client.put(f"/api/v1/cohorts/{COHORT}/teaching-team/{user_id(db, CODER)}", headers=login(client, DOCENTE))
    assert r.status_code == 409 and r.json()["code"] == "person_account"


@pytest.mark.parametrize("account", [CAPT_IA, SEL_IA, CODER, COORD])
def test_only_teachers_of_the_cohort_and_admin_manage_the_team(client, db, account):
    headers = login(client, account)
    assert team(client, headers).status_code == 403
    assert client.put(f"/api/v1/cohorts/{COHORT}/teaching-team/{user_id(db, SEL_IA)}", headers=headers).status_code == 403


def test_teacher_of_another_cohort_cannot_manage_this_one(client, db):
    teacher_id = user_id(db, DOCENTE)
    db.query(RoleAssignment).filter(RoleAssignment.user_id == teacher_id, RoleAssignment.scope_id == COHORT).delete()
    db.commit()
    headers = login(client, DOCENTE)
    assert team(client, headers).status_code == 403
    assert team(client, headers, OTHER).status_code == 200


def test_teacher_has_the_academic_indicators_but_not_the_admission_decision(client, db):
    from app.core.authz import ROLE_PERMISSIONS

    perms = ROLE_PERMISSIONS["docente"]
    assert {"attendance.aggregate", "submissions.aggregate", "competencies.aggregate", "cohort.team.manage"} <= perms
    assert "selection.decide" not in perms
