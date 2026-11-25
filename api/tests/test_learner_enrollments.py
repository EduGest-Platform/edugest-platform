from uuid import uuid4

from sqlalchemy import select

from app.modules.identity.models import User
from app.modules.learning.models import Enrollment
from tests.conftest import ADMIN, ASPIRANTE, CODER, DOCENTE, login
from tests.test_competencies import assess, assign, published_tree

PATH = "/api/v1/me/enrollments"


def own_seed_enrollment(db):
    person_id = db.scalar(select(User.person_id).where(User.email == CODER))
    return db.scalars(select(Enrollment).where(Enrollment.person_id == person_id)).one()


def test_lists_only_the_signed_in_persons_enrollment(client, db):
    enrollment = own_seed_enrollment(db)
    response = client.get(PATH, headers=login(client, CODER))
    assert response.status_code == 200
    item, = response.json()["items"]
    assert item == {
        "enrollment_id": str(enrollment.id),
        "cohort_id": enrollment.cohort_id,
        "cohort_name": "IA aplicada · otoño 2026",
        "status": "activa",
    }


def test_aspirant_and_admin_do_not_receive_other_enrollments(client):
    for email in (ASPIRANTE, ADMIN):
        response = client.get(PATH, headers=login(client, email))
        assert response.status_code == 200
        assert response.json() == {"items": []}
    assert client.get(PATH).status_code == 401


def test_own_attendance_matches_teacher_totals_without_a_cohort_roster(client, db):
    enrollment = own_seed_enrollment(db)
    held_on = "2026-09-14"
    window = {"date_from": held_on, "date_to": held_on}
    teacher_headers = login(client, DOCENTE)
    session = client.post(
        f"/api/v1/cohorts/{enrollment.cohort_id}/attendance-sessions",
        headers=teacher_headers,
        json={"session_date": held_on, "shift": "manana"},
    )
    assert session.status_code == 201
    recorded = client.put(
        f"/api/v1/attendance-sessions/{session.json()['id']}/records/{enrollment.id}",
        headers=teacher_headers,
        json={"status": "presente", "modality": "online"},
    )
    assert recorded.status_code == 200
    learner = client.get(f"{PATH}/{enrollment.id}/attendance", headers=login(client, CODER), params=window)
    assert learner.status_code == 200
    teacher = client.get(
        f"/api/v1/cohorts/{enrollment.cohort_id}/attendance-summary",
        headers=teacher_headers,
        params={**window, "enrollment_id": str(enrollment.id)},
    )
    assert teacher.status_code == 200
    own = learner.json()
    assert set(own) == {"cohort_id", "timezone", "date_from", "date_to", "rule", "totals"}
    assert own["totals"] == teacher.json()["items"][0]
    assert own["totals"]["attended_online_days"] == 0.5
    assert learner.headers["cache-control"] == "no-store"


def test_attendance_requires_an_active_enrollment_owned_by_the_caller(client, db):
    enrollment = own_seed_enrollment(db)
    path = f"{PATH}/{enrollment.id}/attendance"
    owner = login(client, CODER)
    absent = client.get(f"{PATH}/{uuid4()}/attendance", headers=owner)
    assert client.get(path).status_code == 401
    for email in (ASPIRANTE, ADMIN):
        foreign = client.get(path, headers=login(client, email))
        assert (foreign.status_code, foreign.json()["code"]) == (404, absent.json()["code"])
    enrollment.estado = "baja_voluntaria"
    db.commit()
    assert client.get(path, headers=owner).status_code == 404
    assert client.get(PATH, headers=owner).json()["items"][0]["status"] == "baja_voluntaria"


def test_own_competencies_use_the_assigned_framework_and_omit_private_evidence(client, db):
    enrollment = own_seed_enrollment(db)
    path = f"{PATH}/{enrollment.id}/competencies"
    owner = login(client, CODER)
    teacher = login(client, DOCENTE)
    initial = client.get(path, headers=owner)
    assert initial.status_code == 200
    assert initial.json() == {"enrollment_id": str(enrollment.id), "framework_version": None, "current": []}

    first = published_tree(client, teacher, codes=("C1",))
    assert assign(client, teacher, first["id"]).status_code == 200
    assert assess(client, teacher, enrollment.id, first["competencies"][0]["id"], 3).status_code == 201
    current = published_tree(client, teacher, codes=("C1", "C2"))
    assert assign(client, teacher, current["id"]).status_code == 200
    competency = current["competencies"][0]
    assert assess(client, teacher, enrollment.id, competency["id"], 1).status_code == 201
    updated = assess(client, teacher, enrollment.id, competency["id"], 2)
    assert updated.status_code == 201

    result = client.get(path, headers=owner).json()
    assert result["framework_version"] == current["version"]
    assert result["current"] == [
        {
            "competency_id": competency["id"],
            "codigo": "C1",
            "nombre": competency["nombre"],
            "level": 2,
            "assessed_at": updated.json()["assessed_at"],
        },
        {
            "competency_id": current["competencies"][1]["id"],
            "codigo": "C2",
            "nombre": current["competencies"][1]["nombre"],
            "level": None,
            "assessed_at": None,
        },
    ]
    assert client.get(path).status_code == 401
    assert client.get(path, headers=teacher).status_code == 404
