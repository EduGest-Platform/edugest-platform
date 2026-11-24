from sqlalchemy import select

from app.modules.identity.models import User
from app.modules.learning.models import Enrollment
from tests.conftest import ADMIN, ASPIRANTE, CAPT_DATA, CAPT_IA, CODER, DOCENTE, login


def own_enrollment(db):
    person = db.scalar(select(User.person_id).where(User.email == CODER))
    return db.scalar(select(Enrollment).where(Enrollment.person_id == person).order_by(Enrollment.id).limit(1))


def path(enrollment_id):
    return '/api/v1/enrollments/' + str(enrollment_id) + '/documentation'


def test_owner_and_authorized_staff_can_read_minimal_status(client, db):
    row = own_enrollment(db)
    for account in (CODER, CAPT_IA, ADMIN):
        response = client.get(path(row.id), headers=login(client, account))
        assert response.status_code == 200
        assert response.json() == {'enrollment_id': str(row.id), 'state': 'pending', 'version': 1, 'accredited_at': None}
        assert response.headers['cache-control'] == 'no-store'


def test_foreign_staff_and_other_person_cannot_read_status(client, db):
    row = own_enrollment(db)
    assert client.get(path(row.id), headers=login(client, CAPT_DATA)).status_code == 403
    assert client.get(path(row.id), headers=login(client, ASPIRANTE)).status_code == 404
    assert client.get(path(row.id), headers=login(client, DOCENTE)).status_code == 403
