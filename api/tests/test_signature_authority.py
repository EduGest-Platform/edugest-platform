"""Offline authority capture regressions; no database or privilege grants."""
from datetime import datetime, timezone
from types import SimpleNamespace

from app.core.authz import Principal
from app.modules.identity.models import RoleAssignment
from app.modules.selection.authority import signature_authority


def principal(*grants):
    return Principal(user=SimpleNamespace(), assignments=list(grants))


def grant(role='seleccion', scope_type='call', scope_id='CALL-IA'):
    return RoleAssignment(role=role, scope_type=scope_type, scope_id=scope_id)


def test_only_matching_decision_authority_is_captured():
    actor = principal(grant(), grant(scope_id='OTHER'), grant('captacion', 'program', 'P-IA'))
    assert signature_authority(actor, 'P-IA', 'CALL-IA') == [dict(role='seleccion', scope_type='call', scope_id='CALL-IA', permission='selection.decide')]


def test_global_admin_and_program_coordinator_are_deduplicated_and_sorted():
    actor = principal(grant('coordinacion', 'program', 'P-IA'), grant('admin', 'global', None), grant('admin', 'global', None))
    result = signature_authority(actor, 'P-IA', 'CALL-IA')
    assert [entry['role'] for entry in result] == ['admin', 'coordinacion']


def test_revoked_grants_are_not_recorded_and_later_edits_do_not_rewrite_a_snapshot():
    assignment = grant()
    actor = principal(assignment)
    snapshot = signature_authority(actor, 'P-IA', 'CALL-IA')
    assignment.revoked_at = datetime.now(timezone.utc)
    assert signature_authority(actor, 'P-IA', 'CALL-IA') == []
    assert snapshot[0]['scope_id'] == 'CALL-IA'


def test_cohort_teacher_permission_is_not_invented_for_selection():
    assert signature_authority(principal(grant('docente', 'cohort', 'COH-IA')), 'P-IA', 'CALL-IA') == []
