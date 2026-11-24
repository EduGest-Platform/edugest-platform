"""KAN-116: actor identity and filtered audit exports are server-controlled."""
import json

import pytest
from sqlalchemy import func, select

from app.modules.admissions.models import Application, ApplicationEvent
from app.modules.audit.models import AuditEvent
from app.modules.identity.models import User
from tests.conftest import ADMIN, ASPIRANTE, CAPT_DATA, CAPT_IA, CODER, COORD, DOCENTE, SEL_IA, login


def target(db):
    return db.scalar(select(Application).where(Application.call_id == 'CONV-IA-2027A').order_by(Application.codigo))


def test_authenticated_actor_wins_over_spoofed_headers_and_audit_filters_preserve_attribution(client, db):
    application = target(db)
    admin_id = db.scalar(select(User.id).where(User.email == ADMIN))
    expected = []
    for account, role in ((CAPT_IA, 'captacion'), (SEL_IA, 'seleccion')):
        headers = {**login(client, account), 'X-Actor-ID': str(admin_id), 'X-Roles': 'admin', 'X-Request-ID': 'spoofed-client-id'}
        response = client.post(f'/api/v1/applications/{application.id}/events', headers=headers,
                               json={'tipo': 'nota', 'resumen': 'Synthetic private provenance marker'})
        assert response.status_code == 201
        assert response.headers['x-request-id'] != 'spoofed-client-id'
        user = db.scalar(select(User).where(User.email == account))
        assert response.json()['actor'] == user.display_name
        expected.append((str(user.id), role))
    rows = client.get('/api/v1/audit-events', headers=login(client, ADMIN), params={
        'target_type': 'application', 'target_id': str(application.id), 'action': 'application.event_added', 'limit': 500,
    })
    assert rows.status_code == 200
    records = rows.json()
    assert [(row['actor_user_id'], row['actor_roles']) for row in records] == list(reversed(expected))
    assert all(row['target_id'] == str(application.id) for row in records)
    assert 'Synthetic private provenance marker' not in json.dumps(records)


@pytest.mark.parametrize('account', [CAPT_IA, CAPT_DATA, SEL_IA, COORD, DOCENTE, CODER, ASPIRANTE])
def test_filtering_to_a_known_target_never_grants_audit_export_permission(client, db, account):
    application = target(db)
    response = client.get('/api/v1/audit-events', headers=login(client, account), params={
        'target_id': str(application.id), 'target_type': 'application', 'action': 'application.event_added', 'limit': 500,
    })
    assert response.status_code == 403
    assert 'actor_user_id' not in response.json()


def test_denied_cross_program_write_has_a_denial_actor_but_no_success_event(client, db):
    application = target(db)
    actor = db.scalar(select(User).where(User.email == CAPT_DATA))
    headers = {**login(client, CAPT_DATA), 'X-Roles': 'admin'}
    events = db.scalar(select(func.count()).select_from(ApplicationEvent).where(ApplicationEvent.application_id == application.id))
    response = client.post(f'/api/v1/applications/{application.id}/events', headers=headers,
                           json={'tipo': 'nota', 'resumen': 'Synthetic denied marker'})
    assert response.status_code == 403
    assert db.scalar(select(func.count()).select_from(ApplicationEvent).where(ApplicationEvent.application_id == application.id)) == events
    denied = db.scalar(select(AuditEvent).where(AuditEvent.action == 'application.access_denied', AuditEvent.target_id == str(application.id)))
    assert denied.actor_user_id == actor.id and denied.actor_roles == 'captacion'
    assert denied.meta['permission'] == 'applications.crm'
    assert 'Synthetic denied marker' not in json.dumps(denied.meta)
