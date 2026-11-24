"""PostgreSQL edits, tombstones and thread resolution with observed versions."""
from tests.conftest import ADMIN, CAPT_IA, CAPT_DATA, login
from tests.test_discussion_threads import create
from tests.test_discussion_comments import comments


def setup(client):
    headers = login(client, CAPT_IA)
    thread = create(client, headers).json()
    comment = client.post(comments(thread['id']), headers=headers, json={'body': 'Synthetic original'}).json()
    return headers, thread, comment


def test_edit_rejects_stale_version_then_delete_hides_retained_body(client):
    headers, thread, comment = setup(client)
    path = '/api/v1/discussion-comments/' + comment['id']
    edit = client.patch(path, headers=headers, json={'body': 'Synthetic replacement', 'expected_version': comment['version']})
    assert edit.status_code == 200 and edit.json()['version'] == comment['version'] + 1
    assert client.patch(path, headers=headers, json={'body': 'Stale overwrite', 'expected_version': comment['version']}).status_code == 409
    deleted = client.request('DELETE', path, headers=headers, json={'expected_version': edit.json()['version']})
    assert deleted.status_code == 200 and deleted.json()['body'] is None
    listed = client.get(comments(thread['id']), headers=headers).json()
    assert listed['items'][0]['body'] is None
    assert 'Synthetic replacement' not in str(listed)


def test_resolve_reopen_requires_current_thread_version(client):
    headers, thread, _ = setup(client)
    path = '/api/v1/discussion-threads/' + thread['id']
    current = client.get(path, headers=headers).json()
    assert client.post(path + '/resolution', headers=headers, json={'resolved': True, 'expected_version': thread['version']}).status_code == 409
    resolved = client.post(path + '/resolution', headers=headers, json={'resolved': True, 'expected_version': current['version']})
    assert resolved.status_code == 200 and resolved.json()['resolved_at'] is not None
    assert client.post(comments(thread['id']), headers=headers, json={'body': 'Blocked reply'}).status_code == 409
    reopened = client.post(path + '/resolution', headers=headers, json={'resolved': False, 'expected_version': resolved.json()['version']})
    assert reopened.status_code == 200 and reopened.json()['resolved_at'] is None
    assert client.post(comments(thread['id']), headers=headers, json={'body': 'Allowed reply'}).status_code == 201


def test_foreign_scope_cannot_edit_or_delete_even_with_a_known_version(client):
    _, _, comment = setup(client)
    other = login(client, CAPT_DATA)
    path = '/api/v1/discussion-comments/' + comment['id']
    assert client.patch(path, headers=other, json={'body': 'Foreign edit', 'expected_version': 1}).status_code == 403
    assert client.request('DELETE', path, headers=other, json={'expected_version': 1}).status_code == 403
    # An existing global wildcard administrator can moderate inside the verified scope.
    assert client.patch(path, headers=login(client, ADMIN), json={'body': 'Synthetic moderation', 'expected_version': 1}).status_code == 200
