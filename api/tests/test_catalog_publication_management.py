from sqlalchemy import select

from app.modules.audit.models import AuditEvent
from app.modules.catalog.models import Call
from tests.conftest import ADMIN, CAPT_IA, login

CALL = 'CONV-IA-2027A'
PATH = '/api/v1/calls/' + CALL + '/publication'


def test_admin_changes_publication_once_with_audit_and_version(client, db):
    admin = login(client, ADMIN)
    current = client.get(PATH, headers=admin).json()
    body = {'state': 'draft', 'expected_version': current['version']}
    response = client.put(PATH, headers=admin, json=body)
    assert response.status_code == 200
    assert response.json() == {'call_id': CALL, 'state': 'draft', 'version': current['version'] + 1}
    assert client.put(PATH, headers=admin, json=body).status_code == 409
    events = list(db.scalars(select(AuditEvent).where(AuditEvent.action == 'catalog.publication_changed')))
    assert len(events) == 1 and events[0].meta['state'] == 'draft'
    assert db.get(Call, CALL).estado == 'abierta'


def test_non_admin_is_denied_before_call_lookup(client):
    headers = login(client, CAPT_IA)
    for path in (PATH, '/api/v1/calls/UNKNOWN/publication'):
        assert client.get(path, headers=headers).status_code == 403
        assert client.put(path, headers=headers, json={'state': 'published', 'expected_version': 1}).status_code == 403
    assert client.get('/api/v1/catalog/publications', headers=headers).status_code == 403


def test_admin_listing_is_bounded_filterable_and_stable(client):
    headers = login(client, ADMIN)
    response = client.get('/api/v1/catalog/publications?state=published&limit=1&offset=1', headers=headers)
    assert response.status_code == 200
    assert len(response.json()['items']) == 1 and response.json()['total'] == 4
    assert client.get('/api/v1/catalog/publications?limit=101', headers=headers).status_code == 422
