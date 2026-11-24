from types import SimpleNamespace
from datetime import date

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.authz import Principal
from app.modules.catalog.models import Call
from app.modules.catalog.publication_policy import check_publication_version, require_publication_admin, require_published
from app.modules.catalog.publication_schemas import PublicationUpdate, PublicCourseOut
from app.modules.identity.models import RoleAssignment


@pytest.mark.parametrize(('role', 'scope', 'allowed'), [
    ('admin', 'global', True), ('admin', 'program', False),
    ('captacion', 'global', False), ('coordinacion', 'global', False), ('docente', 'global', False),
])
def test_only_existing_global_administration_publishes(role, scope, allowed):
    actor = Principal(user=SimpleNamespace(), assignments=[RoleAssignment(role=role, scope_type=scope, scope_id=None if scope == 'global' else 'P-IA')])
    if allowed:
        require_publication_admin(actor)
    else:
        with pytest.raises(HTTPException) as error:
            require_publication_admin(actor)
        assert error.value.status_code == 403


@pytest.mark.parametrize('state', ['draft', 'unknown', None])
def test_unpublished_or_missing_course_is_not_found(state):
    row = None if state is None else SimpleNamespace(publication_state=state)
    with pytest.raises(HTTPException) as error:
        require_published(row)
    assert error.value.status_code == 404


def test_publication_is_independent_of_admission_state():
    require_published(SimpleNamespace(publication_state='published', estado='cerrada'))
    assert Call.__table__.c.publication_state.default.arg == 'draft'
    assert Call.__table__.c.publication_state.server_default.arg == 'draft'


def test_stale_publication_version_requires_refresh():
    row = SimpleNamespace(publication_version=2)
    check_publication_version(row, 2)
    with pytest.raises(HTTPException) as error:
        check_publication_version(row, 1)
    assert error.value.status_code == 409


@pytest.mark.parametrize('extra', [{'expected_version': 0}, {'state': 'archived'}, {'actor_id': 'synthetic'}])
def test_publication_contract_rejects_invalid_or_spoofed_fields(extra):
    with pytest.raises(ValidationError):
        PublicationUpdate(**({'state': 'published', 'expected_version': 1} | extra))


def test_public_projection_contains_only_offer_fields():
    assert set(PublicCourseOut.model_fields) == {
        'id', 'program_id', 'program_name', 'name', 'opens_on', 'closes_on', 'capacity', 'admission_state'}


@pytest.mark.parametrize('row', [None, SimpleNamespace(publication_state='draft')])
def test_registration_rejects_unpublished_offer_before_person_or_application_write(row):
    from app.modules.admissions.service import create_application

    class LookupOnlyDatabase:
        def scalar(self, query):
            return row

    with pytest.raises(HTTPException) as error:
        create_application(LookupOnlyDatabase(), SimpleNamespace(call_id='SYNTHETIC'), None)
    assert error.value.status_code == 404


@pytest.mark.parametrize('changes', [{'nombre': '   '}, {'plazas': -1}, {'closes_on': date(2029, 1, 1)}])
def test_incomplete_offer_cannot_be_published(changes):
    from app.modules.catalog.publication_policy import require_publishable

    call = SimpleNamespace(**({'nombre': 'Synthetic course', 'plazas': 0,
                               'opens_on': date(2030, 1, 1), 'closes_on': date(2030, 2, 1)} | changes))
    with pytest.raises(HTTPException) as error:
        require_publishable(call)
    assert error.value.status_code == 422


def test_minimal_projection_does_not_expose_other_model_attributes():
    from app.modules.catalog.public_service import course_out
    from app.modules.catalog.publication_policy import require_publishable

    canary = 'SYNTHETIC-INTERNAL-POLICY-CANARY'
    call = SimpleNamespace(id='SYNTHETIC', program_id='P-IA', nombre='Synthetic course', plazas=0,
                           opens_on=date(2030, 1, 1), closes_on=date(2030, 2, 1), estado='cerrada',
                           codigo_prefix=canary, next_seq=123, silence_days=99, publication_version=7)
    program = SimpleNamespace(nombre='Synthetic program', descripcion=canary)
    require_publishable(call)
    projected = course_out(call, program).model_dump_json()
    assert canary not in projected
    assert 'publication_version' not in projected and 'silence_days' not in projected
