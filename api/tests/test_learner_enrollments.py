from sqlalchemy import select

from app.modules.identity.models import User
from app.modules.learning.models import Enrollment
from tests.conftest import ADMIN, ASPIRANTE, CODER, login

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
