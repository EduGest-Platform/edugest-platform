import json

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.security import hash_password
from app.modules.audit.models import AuditEvent
from app.modules.identity.models import User
from app.modules.integrations.github.client import GithubRateLimited, GithubReadOnlyClient, HttpResponse
from app.modules.learning import portfolio
from app.modules.learning.models import Enrollment
from tests.conftest import ADMIN, ASPIRANTE, CODER, login


@pytest.fixture
def enrollment(db):
    return db.scalar(select(Enrollment).join(User, User.person_id == Enrollment.person_id).where(User.email == CODER))


def path(enrollment):
    return f'/api/v1/me/enrollments/{enrollment.id}/portfolio'


def test_learner_controls_own_portfolio_and_audit_omits_link(client, db, enrollment):
    owner = login(client, CODER)
    endpoint = path(enrollment)
    assert client.get(endpoint).status_code == 401
    other = db.scalar(select(Enrollment).where(Enrollment.person_id != enrollment.person_id).limit(1))
    other_email = 'another-learner@example.test'
    db.add(User(person_id=other.person_id, display_name='Another synthetic learner', email=other_email,
                password_hash=hash_password(settings.demo_password)))
    db.commit()
    for email in (ADMIN, ASPIRANTE, other_email):
        assert client.get(endpoint, headers=login(client, email)).status_code == 404
    assert client.get(endpoint, headers=owner).json()['url'] is None
    raw = 'https://www.github.com/Synthetic-Org/Sample.git/'
    saved = client.put(endpoint, headers=owner, json={'url': raw, 'authorized': True})
    assert saved.status_code == 200
    assert saved.json()['url'] == 'https://github.com/synthetic-org/sample'
    assert client.put(endpoint, headers=owner, json={'url': raw, 'authorized': True}).json() == saved.json()
    assert client.post(endpoint + '/metadata', headers=owner).status_code == 409
    assert not client.get(endpoint, headers=owner).json()['can_lookup']
    assert client.delete(endpoint, headers=login(client, ADMIN)).status_code == 404

    enrollment.estado = 'baja_voluntaria'
    db.commit()
    assert not client.get(endpoint, headers=owner).json()['can_edit']
    assert client.put(endpoint, headers=owner, json={'url': raw, 'authorized': True}).status_code == 409
    assert client.delete(endpoint, headers=owner).status_code == 204
    assert client.delete(endpoint, headers=owner).status_code == 204
    actions = db.scalars(select(AuditEvent).where(AuditEvent.target_id == str(enrollment.id),
                                                 AuditEvent.action.startswith('portfolio.'))).all()
    assert {row.action for row in actions} == {'portfolio.link_saved', 'portfolio.link_removed'}
    assert len(actions) == 2 and all(row.meta == {} for row in actions)


@pytest.mark.parametrize('url', [
    'http://github.com/demo/project',
    'https://github.com/demo/project?key=extra',
    'https://github.com/demo/project/blob/main',
    'https://github.com/demo',
    'https://example.test/demo/project',
])
def test_rejects_noncanonical_repository_targets(client, enrollment, url):
    response = client.put(path(enrollment), headers=login(client, CODER), json={'url': url, 'authorized': True})
    assert response.status_code == 422


def test_public_lookup_is_opt_in_minimal_and_uses_no_credentials(client, enrollment, monkeypatch):
    owner = login(client, CODER)
    endpoint = path(enrollment)
    target = 'https://github.com/synthetic-org/sample'
    assert client.put(endpoint, headers=owner, json={'url': target, 'authorized': False}).status_code == 422
    assert client.put(endpoint, headers=owner, json={'url': target, 'authorized': True}).status_code == 200

    calls = []
    payload = {'private': False, 'visibility': 'public', 'pushed_at': '2026-11-20T09:00:00Z', 'language': 'Python',
               'description': 'Other metadata is not returned'}

    class FakeGithub:
        def __init__(self, *, timeout):
            assert timeout > 0

        def get_json(self, route):
            calls.append(route)
            if not payload:
                raise GithubRateLimited()
            return payload

    monkeypatch.setattr(portfolio, 'GithubReadOnlyClient', FakeGithub)
    assert client.post(endpoint + '/metadata', headers=owner).status_code == 409 and calls == []
    monkeypatch.setattr(settings, 'portfolio_github_lookup', True)
    assert client.post(endpoint + '/metadata', headers=login(client, ASPIRANTE)).status_code == 404 and calls == []
    response = client.post(endpoint + '/metadata', headers=owner)
    assert response.status_code == 200 and calls == ['/repos/synthetic-org/sample']
    assert response.json() == {'primary_language': 'Python', 'last_push_at': '2026-11-20T09:00:00Z'}
    payload['private'] = True
    assert client.post(endpoint + '/metadata', headers=owner).status_code == 404
    payload.clear()
    assert client.post(endpoint + '/metadata', headers=owner).status_code == 429
    assert client.get(endpoint, headers=owner).json()['url'] == target


def test_portfolio_write_and_lookup_reject_nonowners_and_inactive_enrollment(client, db, enrollment, monkeypatch):
    endpoint = path(enrollment)
    owner = login(client, CODER)
    target = 'https://github.com/synthetic-org/original'
    replacement = 'https://github.com/synthetic-org/replacement'
    assert client.put(endpoint, headers=owner, json={'url': target, 'authorized': True}).status_code == 200
    monkeypatch.setattr(settings, 'portfolio_github_lookup', True)

    def unexpected_client(**kwargs):
        pytest.fail('Unauthorized or inactive lookup must not contact GitHub')

    monkeypatch.setattr(portfolio, 'GithubReadOnlyClient', unexpected_client)
    for email in (ADMIN, ASPIRANTE):
        headers = login(client, email)
        assert client.put(endpoint, headers=headers, json={'url': replacement, 'authorized': True}).status_code == 404
        assert client.post(endpoint + '/metadata', headers=headers).status_code == 404
        assert client.delete(endpoint, headers=headers).status_code == 404
    enrollment.estado = 'baja_voluntaria'
    db.commit()
    assert client.post(endpoint + '/metadata', headers=owner).status_code == 409
    assert client.put(endpoint, headers=owner, json={'url': replacement, 'authorized': True}).status_code == 409
    view = client.get(endpoint, headers=owner).json()
    assert view['url'] == target and not view['can_lookup'] and not view['can_edit']
    assert client.delete(endpoint, headers=owner).status_code == 204
    assert client.get(endpoint, headers=owner).json()['url'] is None


@pytest.mark.parametrize(
    'status,payload,expected',
    [
        (200, {'private': False, 'visibility': 'internal'}, 404),
        (200, {'visibility': 'public'}, 404),
        (200, {'private': True, 'visibility': 'private'}, 404),
        (200, {'private': False, 'visibility': 'public', 'language': ['invalid']}, 502),
        (200, {'private': False, 'visibility': 'public', 'pushed_at': 'invalid'}, 502),
        (200, [], 502),
        (302, {'message': 'Moved'}, 502),
        (401, {'message': 'Rejected'}, 502),
        (404, {'message': 'Not found'}, 404),
        (429, {'message': 'Limited'}, 429),
        (503, {'message': 'Unavailable'}, 502),
    ],
)
def test_lookup_fails_closed_and_never_exposes_upstream_payload(
    client, db, enrollment, monkeypatch, status, payload, expected,
):
    owner = login(client, CODER)
    endpoint = path(enrollment)
    target = 'https://github.com/synthetic-org/portfolio'
    assert client.put(endpoint, headers=owner, json={'url': target, 'authorized': True}).status_code == 200
    monkeypatch.setattr(settings, 'portfolio_github_lookup', True)
    calls = []

    def transport(request):
        calls.append(request)
        headers = {'location': 'https://example.test/never-follow'}
        return HttpResponse(status, headers, json.dumps(payload).encode())

    def public_client(*, timeout):
        return GithubReadOnlyClient(timeout=timeout, transport=transport)

    monkeypatch.setattr(portfolio, 'GithubReadOnlyClient', public_client)
    response = client.post(endpoint + '/metadata', headers=owner)
    assert response.status_code == expected
    assert 'never-follow' not in response.text
    assert 'synthetic-org/portfolio' not in response.text
    assert len(calls) == 1
    assert calls[0].method == 'GET'
    assert calls[0].url == 'https://api.github.com/repos/synthetic-org/portfolio'
    assert 'Authorization' not in calls[0].headers
    assert client.get(endpoint, headers=owner).json()['url'] == target
    events = db.scalars(select(AuditEvent).where(
        AuditEvent.target_id == str(enrollment.id),
        AuditEvent.action.startswith('portfolio.'),
    )).all()
    assert len(events) == 1 and events[0].meta == {}
