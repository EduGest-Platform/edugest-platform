"""PostgreSQL thread API integration and transaction boundaries."""
from sqlalchemy import func, select

from app.core import audit
from app.modules.admissions.models import Application
from app.modules.discussions.models import DiscussionThread
from tests.conftest import ADMIN, CAPT_DATA, CAPT_IA, SEL_IA, login


def create(client, headers, **changes):
    return client.post('/api/v1/discussion-threads', headers=headers,
                       json={'scope_type': 'program', 'program_id': 'P-IA', 'subject': 'Synthetic internal topic', **changes})


def test_program_threads_are_scoped_and_call_assignment_is_not_program_wide(client):
    one = create(client, login(client, CAPT_IA))
    assert one.status_code == 201, one.text
    create(client, login(client, ADMIN), program_id='P-DATA')
    listed = client.get('/api/v1/discussion-threads', params={'scope_type': 'program', 'program_id': 'P-IA'}, headers=login(client, CAPT_IA))
    assert listed.status_code == 200 and listed.json()['total'] == 1
    assert listed.json()['items'][0]['id'] == one.json()['id']
    for account in (CAPT_DATA, SEL_IA):
        assert client.get('/api/v1/discussion-threads/' + one.json()['id'], headers=login(client, account)).status_code == 403


def test_selector_uses_its_application_scope_without_changing_application_state(client, db):
    target = db.scalar(select(Application).where(Application.call_id == 'CONV-IA-2027A'))
    before = target.stage
    response = client.post('/api/v1/discussion-threads', headers=login(client, SEL_IA), json={
        'scope_type': 'application', 'application_id': str(target.id), 'subject': 'Synthetic selection discussion'})
    assert response.status_code == 201
    db.refresh(target)
    assert target.stage == before


def test_thread_creation_rolls_back_if_audit_fails(client, db, monkeypatch):
    headers = login(client, CAPT_IA)
    before = db.scalar(select(func.count()).select_from(DiscussionThread))
    original = audit.record
    def fail(db, actor, action, *args, **kwargs):
        if action == 'discussion.thread_created':
            raise RuntimeError('Synthetic audit failure')
        return original(db, actor, action, *args, **kwargs)
    monkeypatch.setattr(audit, 'record', fail)
    assert create(client, headers).status_code == 500
    assert db.scalar(select(func.count()).select_from(DiscussionThread)) == before


def test_board_directory_only_lists_authorized_programs(client):
    directory = '/api/v1/discussion-programs'
    assert client.get(directory).status_code == 401
    for account, expected in ((CAPT_IA, {'P-IA'}), (CAPT_DATA, {'P-DATA'}), (SEL_IA, set())):
        response = client.get(directory, headers=login(client, account))
        assert response.status_code == 200, response.text
        assert {row['id'] for row in response.json()} == expected
        assert all(row['can_write'] is True for row in response.json())


def test_program_board_counts_only_threads_matching_the_resolution_filter(client):
    headers = login(client, CAPT_IA)
    open_thread = create(client, headers, subject='Open synthetic topic').json()
    closed = create(client, headers, subject='Resolved synthetic topic').json()
    change = client.post(f"/api/v1/discussion-threads/{closed['id']}/resolution", headers=headers,
                         json={'resolved': True, 'expected_version': closed['version']})
    assert change.status_code == 200, change.text
    path = '/api/v1/discussion-threads'
    query = {'scope_type': 'program', 'program_id': 'P-IA', 'limit': 1}
    for resolved, expected in ((False, open_thread), (True, closed)):
        response = client.get(path, params={**query, 'resolved': resolved}, headers=headers)
        assert response.status_code == 200
        assert response.json()['total'] == 1
        assert [row['id'] for row in response.json()['items']] == [expected['id']]


def test_cross_program_resolution_cannot_change_thread(client):
    owner = login(client, CAPT_IA)
    outsider = login(client, CAPT_DATA)
    created = create(client, owner)
    assert created.status_code == 201, created.text
    thread = created.json()
    path = f"/api/v1/discussion-threads/{thread['id']}/resolution"
    for resolved in (True, False):
        forbidden = client.post(path, headers=outsider,
                                json={'resolved': resolved, 'expected_version': thread['version']})
        assert forbidden.status_code == 403, forbidden.text
        allowed = client.post(path, headers=owner,
                              json={'resolved': resolved, 'expected_version': thread['version']})
        assert allowed.status_code == 200, allowed.text
        thread = allowed.json()
        listed = client.get('/api/v1/discussion-threads', headers=owner,
                            params={'scope_type': 'program', 'program_id': 'P-IA', 'resolved': resolved})
        assert listed.status_code == 200
        assert [row['id'] for row in listed.json()['items']] == [thread['id']]
