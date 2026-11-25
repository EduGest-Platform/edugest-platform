import uuid

from sqlalchemy import func, select

from app.modules.audit.models import AuditEvent
from app.modules.catalog.models import Call
from app.modules.identity.models import RoleAssignment
from app.modules.learning.models import Enrollment
from tests.conftest import ADMIN, CAPT_IA, login
from tests.test_enrollment_documentation_reads import own_enrollment, path
from tests.test_selection_decisions import IA_CALL, decide, make_application, make_cohort


def admitted_enrollment(client, db):
    db.get(Call, IA_CALL).selection_quorum = 1
    db.commit()
    make_cohort(db)
    application = make_application(db)
    response = decide(client, login(client, ADMIN), application.id)
    assert response.status_code == 201
    return db.get(Enrollment, uuid.UUID(response.json()['enrollment_id']))


def test_admin_accredits_once_without_altering_roles_or_academic_state(client, db):
    row = admitted_enrollment(client, db)
    admin = login(client, ADMIN)
    roles = db.scalar(select(func.count()).select_from(RoleAssignment))
    response = client.post(path(row.id) + '/accredit', headers=admin, json={'expected_version': 1})
    assert response.status_code == 200 and response.json()['state'] == 'accredited'
    assert response.json()['version'] == 2 and response.json()['accredited_at'] is not None
    assert client.post(path(row.id) + '/accredit', headers=admin, json={'expected_version': 1}).status_code == 409
    repeated = client.post(path(row.id) + '/accredit', headers=admin, json={'expected_version': 2})
    assert repeated.status_code == 200 and repeated.json() == response.json()
    assert db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action == 'enrollment.documentation_accredited')) == 1
    db.refresh(row)
    assert row.estado == 'activa' and row.documentation_accredited_by is not None
    assert db.scalar(select(func.count()).select_from(RoleAssignment)) == roles


def test_recruiting_cannot_accredit_and_legacy_admission_is_not_inferred(client, db):
    row = own_enrollment(db)
    body = {'expected_version': 1}
    assert client.post(path(row.id) + '/accredit', headers=login(client, CAPT_IA), json=body).status_code == 403
    response = client.post(path(row.id) + '/accredit', headers=login(client, ADMIN), json=body)
    assert response.status_code == 409 and response.json()['code'] == 'documentation_admission_required'
