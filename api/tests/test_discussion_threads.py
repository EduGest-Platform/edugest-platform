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
