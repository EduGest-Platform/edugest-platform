from types import SimpleNamespace

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
