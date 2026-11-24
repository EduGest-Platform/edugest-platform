"""KAN-244: PostgreSQL adversarial scope, content, audit and concurrent-edit checks."""
import json
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core import audit
from app.main import app
from app.modules.admissions.models import Application
from app.modules.audit.models import AuditEvent
from app.modules.discussions.models import DiscussionComment, DiscussionThread
from app.modules.learning.models import Enrollment
from app.modules.selection.models import SelectionDecision
from tests.conftest import ASPIRANTE, CAPT_DATA, CAPT_IA, CODER, COORD, DOCENTE, SEL_IA, login
from tests.test_discussion_threads import create
from tests.test_discussion_comments import comments


def prepare(client):
    owner = login(client, CAPT_IA)
    thread = create(client, owner).json()
    comment = client.post(comments(thread['id']), headers=owner, json={'body': 'Synthetic protected content'}).json()
    return owner, thread, comment


def stored(db, thread_id, comment_id):
    db.expire_all()
    thread = db.get(DiscussionThread, uuid.UUID(thread_id))
    comment = db.get(DiscussionComment, uuid.UUID(comment_id))
    return (thread.version, thread.resolved_at, thread.resolved_by, comment.version, comment.body, comment.deleted_at, comment.deleted_by)


@pytest.mark.parametrize('account', [CAPT_DATA, SEL_IA, DOCENTE, COORD, CODER, ASPIRANTE])
def test_unauthorized_roles_cannot_use_any_program_discussion_surface(client, db, account):
    _, thread, comment = prepare(client)
    actor = login(client, account)
    before = stored(db, thread['id'], comment['id'])
    base = '/api/v1/discussion-threads/' + thread['id']
    operations = [
        ('GET', '/api/v1/discussion-threads?scope_type=program&program_id=P-IA', None),
        ('GET', base, None), ('GET', comments(thread['id']), None),
        ('POST', comments(thread['id']), {'body': 'Denied reply', 'parent_id': comment['id']}),
        ('PATCH', '/api/v1/discussion-comments/' + comment['id'], {'body': 'Denied edit', 'expected_version': 1}),
        ('DELETE', '/api/v1/discussion-comments/' + comment['id'], {'expected_version': 1}),
        ('POST', base + '/resolution', {'resolved': True, 'expected_version': 2}),
    ]
    for method, path, body in operations:
        response = client.request(method, path, headers=actor, json=body)
        assert response.status_code == 403, (method, path, response.text)
        assert 'Synthetic protected content' not in response.text
    assert stored(db, thread['id'], comment['id']) == before


def test_same_scope_writer_can_reply_but_cannot_edit_delete_or_resolve_another_authors_content(client, db):
    owner = login(client, CAPT_IA)
    application = db.scalar(select(Application).where(Application.call_id == 'CONV-IA-2027A'))
    thread = client.post('/api/v1/discussion-threads', headers=owner, json={
        'scope_type': 'application', 'application_id': str(application.id), 'subject': 'Synthetic shared scope'}).json()
    original = client.post(comments(thread['id']), headers=owner, json={'body': 'Synthetic owner text'}).json()
    other = login(client, SEL_IA)
    assert client.post(comments(thread['id']), headers=other, json={'body': 'Synthetic allowed reply', 'parent_id': original['id']}).status_code == 201
    path = '/api/v1/discussion-comments/' + original['id']
    assert client.patch(path, headers=other, json={'body': 'Denied replacement', 'expected_version': 1}).status_code == 403
    assert client.request('DELETE', path, headers=other, json={'expected_version': 1}).status_code == 403
    assert client.post('/api/v1/discussion-threads/' + thread['id'] + '/resolution', headers=other,
                       json={'resolved': True, 'expected_version': 3}).status_code == 403


def test_markup_is_json_text_and_never_copied_to_audit_metadata(client, db):
    owner, thread, _ = prepare(client)
    markup = '<img src=x onerror="window.syntheticMarker=1">'
    response = client.post(comments(thread['id']), headers=owner, json={'body': markup})
    assert response.status_code == 201 and response.json()['body'] == markup
    assert response.headers['content-type'].startswith('application/json')
    assert response.headers['x-content-type-options'] == 'nosniff'
    records = list(db.scalars(select(AuditEvent).where(AuditEvent.action.like('discussion.%'))))
    assert markup not in json.dumps([row.meta for row in records])
    assert 'Synthetic internal topic' not in json.dumps([row.meta for row in records])


@pytest.mark.parametrize(('method', 'suffix', 'action'), [
    ('PATCH', 'comment', 'discussion.comment_edited'),
    ('DELETE', 'comment', 'discussion.comment_deleted'),
    ('POST', 'resolution', 'discussion.thread_resolved'),
])
def test_failed_audit_rolls_back_edits_tombstones_and_resolution(client, db, monkeypatch, method, suffix, action):
    owner, thread, comment = prepare(client)
    before = stored(db, thread['id'], comment['id'])
    audit_before = db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action == action))
    original = audit.record
    def fail(db, actor, current_action, *args, **kwargs):
        if current_action == action:
            db.flush()
            raise RuntimeError('Synthetic audit failure')
        return original(db, actor, current_action, *args, **kwargs)
    monkeypatch.setattr(audit, 'record', fail)
    if suffix == 'resolution':
        path = '/api/v1/discussion-threads/' + thread['id'] + '/resolution'
        body = {'resolved': True, 'expected_version': before[0]}
    else:
        path = '/api/v1/discussion-comments/' + comment['id']
        body = {'expected_version': comment['version']}
        if method == 'PATCH':
            body['body'] = 'Synthetic rollback replacement'
    assert client.request(method, path, headers=owner, json=body).status_code == 500
    assert stored(db, thread['id'], comment['id']) == before
    assert db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action == action)) == audit_before


def test_concurrent_edits_of_the_same_observed_version_have_one_winner(client, db):
    owner, thread, comment = prepare(client)
    path = '/api/v1/discussion-comments/' + comment['id']
    with TestClient(app) as first, TestClient(app) as second:
        def edit(pair):
            caller, text = pair
            return caller.patch(path, headers=owner, json={'body': text, 'expected_version': 1}).status_code
        with ThreadPoolExecutor(2) as pool:
            codes = sorted(pool.map(edit, [(first, 'Synthetic first edit'), (second, 'Synthetic second edit')]))
    assert codes == [200, 409]
    final = stored(db, thread['id'], comment['id'])
    assert final[3] == 2 and final[4] in {'Synthetic first edit', 'Synthetic second edit'}
    assert db.scalar(select(func.count()).select_from(AuditEvent).where(AuditEvent.action == 'discussion.comment_edited')) == 1


def test_comment_lifecycle_never_changes_admission_or_enrollment(client, db):
    owner = login(client, CAPT_IA)
    application = db.scalar(select(Application).where(Application.call_id == 'CONV-IA-2027A'))
    before = (application.stage, db.scalar(select(func.count()).select_from(Enrollment)),
              db.scalar(select(func.count()).select_from(SelectionDecision)))
    thread = client.post('/api/v1/discussion-threads', headers=owner, json={
        'scope_type': 'application', 'application_id': str(application.id), 'subject': 'Synthetic non-decision discussion'}).json()
    comment = client.post(comments(thread['id']), headers=owner, json={'body': 'Synthetic note, not a decision'}).json()
    path = '/api/v1/discussion-comments/' + comment['id']
    edited = client.patch(path, headers=owner, json={'body': 'Synthetic revised note', 'expected_version': comment['version']})
    assert edited.status_code == 200
    assert client.request('DELETE', path, headers=owner, json={'expected_version': edited.json()['version']}).status_code == 200
    thread_path = '/api/v1/discussion-threads/' + thread['id']
    current = client.get(thread_path, headers=owner).json()
    assert client.post(thread_path + '/resolution', headers=owner, json={'resolved': True, 'expected_version': current['version']}).status_code == 200
    db.refresh(application)
    after = (application.stage, db.scalar(select(func.count()).select_from(Enrollment)),
             db.scalar(select(func.count()).select_from(SelectionDecision)))
    assert after == before
