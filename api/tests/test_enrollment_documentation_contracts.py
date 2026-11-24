import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.authz import Principal
from app.modules.identity.models import RoleAssignment
from app.modules.learning.documentation_policy import check_documentation_version, require_documentation_admin, require_documentation_read
from app.modules.learning.documentation_schemas import DocumentationOut, DocumentationWrite
from app.modules.learning.models import Enrollment


def principal(role=None, kind='global', scope_id=None, person_id=None):
    return Principal(user=SimpleNamespace(person_id=person_id), assignments=[] if role is None else [
        RoleAssignment(role=role, scope_type=kind, scope_id=scope_id)])


@pytest.mark.parametrize('role,kind,allowed', [('admin', 'global', True), ('admin', 'program', False),
    ('captacion', 'global', False), ('seleccion', 'global', False), ('docente', 'global', False)])
def test_only_existing_global_administration_can_accredit(role, kind, allowed):
    actor = principal(role, kind, 'P-IA' if kind == 'program' else None)
    if allowed:
        require_documentation_admin(actor)
    else:
        with pytest.raises(HTTPException) as error:
            require_documentation_admin(actor)
        assert error.value.status_code == 403


def test_owner_can_read_own_status_but_not_another_persons():
    identity = uuid.uuid4()
    actor = principal(person_id=identity)
    cohort = SimpleNamespace(id='COH-IA', program_id='P-IA', call_id='CONV-IA')
    require_documentation_read(actor, SimpleNamespace(person_id=identity), cohort)
    with pytest.raises(HTTPException) as error:
        require_documentation_read(actor, SimpleNamespace(person_id=uuid.uuid4()), cohort)
    assert error.value.status_code == 404


def test_staff_read_follows_existing_application_scope():
    row = SimpleNamespace(person_id=uuid.uuid4())
    cohort = SimpleNamespace(id='COH-IA', program_id='P-IA', call_id='CONV-IA')
    require_documentation_read(principal('captacion', 'program', 'P-IA'), row, cohort)
    with pytest.raises(HTTPException) as error:
        require_documentation_read(principal('captacion', 'program', 'P-DATA'), row, cohort)
    assert error.value.status_code == 403


@pytest.mark.parametrize('fields', [{'expected_version': 0}, {'expected_version': 1, 'accredited_by': str(uuid.uuid4())},
                                  {'expected_version': 1, 'document_url': 'https://synthetic.example'}])
def test_input_cannot_spoof_an_actor_or_upload_document_metadata(fields):
    with pytest.raises(ValidationError):
        DocumentationWrite(**fields)


def test_historical_enrollments_do_not_infer_accreditation_and_response_minimizes_identity():
    assert Enrollment.__table__.c.documentation_state.server_default.arg == 'pending'
    assert set(DocumentationOut.model_fields) == {'enrollment_id', 'state', 'version', 'accredited_at'}


def test_stale_documentation_write_is_a_conflict():
    row = SimpleNamespace(documentation_version=2)
    check_documentation_version(row, 2)
    with pytest.raises(HTTPException) as error:
        check_documentation_version(row, 1)
    assert error.value.status_code == 409


@pytest.mark.parametrize('broken', [None, 'inactive', 'unlinked', 'waiting_list', 'person', 'call', 'decision'])
def test_accreditation_requires_a_coherent_active_admission(broken):
    from app.modules.learning.documentation_policy import require_accreditation_eligibility

    person, application_id = uuid.uuid4(), uuid.uuid4()
    row = SimpleNamespace(estado='activa', person_id=person, application_id=application_id, cohort_id='COH-IA')
    application = SimpleNamespace(id=application_id, person_id=person, stage='admitida', call_id='CALL-IA')
    cohort = SimpleNamespace(id='COH-IA', call_id='CALL-IA')
    if broken == 'inactive':
        row.estado = 'baja_voluntaria'
    elif broken == 'unlinked':
        application = None
    elif broken == 'waiting_list':
        application.stage = 'lista_espera'
    elif broken == 'person':
        application.person_id = uuid.uuid4()
    elif broken == 'call':
        cohort.call_id = 'CALL-DATA'
    if broken is None:
        require_accreditation_eligibility(row, application, cohort, True)
    else:
        with pytest.raises(HTTPException) as error:
            require_accreditation_eligibility(row, application, cohort, broken != 'decision')
        assert error.value.status_code == 409
