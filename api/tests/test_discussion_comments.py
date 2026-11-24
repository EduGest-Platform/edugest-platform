"""PostgreSQL comment/reply transaction boundaries."""
import uuid

from sqlalchemy import func, select

from app.core import audit
from app.core.db import utcnow
from app.modules.discussions.models import DiscussionComment, DiscussionThread
from tests.conftest import CAPT_IA, login
from tests.test_discussion_threads import create


def comments(thread_id):
    return f'/api/v1/discussion-threads/{thread_id}/comments'


def test_root_and_reply_keep_parent_author_and_server_revision(client):
    headers = login(client, CAPT_IA)
    thread = create(client, headers).json()
    root = client.post(comments(thread['id']), headers=headers, json={'body': ' Synthetic root '})
    assert root.status_code == 201, root.text
    reply = client.post(comments(thread['id']), headers=headers, json={'body': 'Synthetic reply', 'parent_id': root.json()['id']})
    assert reply.status_code == 201 and reply.json()['parent_id'] == root.json()['id']
    listed = client.get(comments(thread['id']), headers=headers).json()
    assert listed['total'] == 2
    assert [item['body'] for item in listed['items']] == ['Synthetic root', 'Synthetic reply']
    updated = client.get('/api/v1/discussion-threads/' + thread['id'], headers=headers).json()
    assert updated['version'] == thread['version'] + 2


def test_parent_from_another_thread_is_not_available(client, db):
    headers = login(client, CAPT_IA)
    one, two = create(client, headers).json(), create(client, headers).json()
    parent = client.post(comments(one['id']), headers=headers, json={'body': 'Synthetic root'}).json()
    response = client.post(comments(two['id']), headers=headers, json={'body': 'Synthetic invalid reply', 'parent_id': parent['id']})
    assert response.status_code == 404 and response.json()['code'] == 'parent_not_found'
    assert db.scalar(select(func.count()).select_from(DiscussionComment)) == 1


def test_resolved_thread_rejects_new_comments(client, db):
    headers = login(client, CAPT_IA)
    result = create(client, headers).json()
    thread = db.get(DiscussionThread, uuid.UUID(result['id']))
    thread.resolved_by, thread.resolved_at = thread.created_by, utcnow()
    db.commit()
    response = client.post(comments(result['id']), headers=headers, json={'body': 'Synthetic comment'})
    assert response.status_code == 409 and response.json()['code'] == 'thread_resolved'


def test_comment_and_thread_version_roll_back_with_failed_audit(client, db, monkeypatch):
    headers = login(client, CAPT_IA)
    thread = create(client, headers).json()
    original = audit.record
    def fail(db, actor, action, *args, **kwargs):
        if action == 'discussion.comment_created':
            raise RuntimeError('Synthetic audit failure')
        return original(db, actor, action, *args, **kwargs)
    monkeypatch.setattr(audit, 'record', fail)
    assert client.post(comments(thread['id']), headers=headers, json={'body': 'Synthetic comment'}).status_code == 500
    assert db.scalar(select(func.count()).select_from(DiscussionComment)) == 0
    db.expire_all()
    assert db.get(DiscussionThread, uuid.UUID(thread['id'])).version == thread['version']
