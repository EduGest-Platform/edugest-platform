from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.authz import Principal
from app.modules.identity.models import RoleAssignment
from app.modules.learning.overview_policy import require_overview_access, visible_has_data
from app.modules.learning.overview_schemas import CohortProgressOverview, OverviewAttendance


@pytest.mark.parametrize('role,kind,scope,allowed', [
    ('admin', 'global', None, True), ('coordinacion', 'global', None, True),
    ('docente', 'cohort', 'COH-IA', True), ('docente', 'cohort', 'COH-DATA', False),
    ('coordinacion', 'program', 'P-IA', True), ('coordinacion', 'program', 'P-DATA', False),
    ('captacion', 'program', 'P-IA', False), ('seleccion', 'call', 'CALL-IA', False),
])
def test_overview_uses_existing_aggregate_permissions_in_the_actual_cohort(role, kind, scope, allowed):
    actor = Principal(user=SimpleNamespace(), assignments=[RoleAssignment(role=role, scope_type=kind, scope_id=scope)])
    cohort = SimpleNamespace(id='COH-IA', program_id='P-IA', call_id='CALL-IA')
    if allowed:
        require_overview_access(actor, cohort)
    else:
        with pytest.raises(HTTPException) as error:
            require_overview_access(actor, cohort)
        assert error.value.status_code == 403


@pytest.mark.parametrize('suppressed,available,expected', [(True, True, None), (True, False, None), (False, True, True), (False, False, False)])
def test_suppressed_groups_do_not_reveal_record_presence(suppressed, available, expected):
    assert visible_has_data(suppressed, available) is expected


def test_overview_contract_has_no_per_person_rows_or_names():
    assert set(CohortProgressOverview.model_fields) == {'cohort_id', 'timezone', 'generated_at', 'aggregate_only', 'attendance', 'submissions', 'competencies'}
    assert set(OverviewAttendance.model_fields) == {'date_from', 'date_to', 'rule', 'has_data', 'totals'}
