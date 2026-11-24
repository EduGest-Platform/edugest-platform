from sqlalchemy import func, select

from app.modules.admissions.models import Application
from app.modules.catalog.models import Call
from app.modules.identity.models import Person
from tests.conftest import ADMIN, login, new_application

CALL = 'CONV-IA-2027A'


def test_legacy_public_list_excludes_drafts_for_every_caller(client, db):
    row = db.get(Call, CALL)
    row.publication_state = 'draft'
    db.commit()
    for headers in ({}, login(client, ADMIN)):
        for query in ('', '?estado=abierta'):
            response = client.get('/api/v1/calls' + query, headers=headers)
            assert response.status_code == 200
            assert CALL not in {item['id'] for item in response.json()}


def test_direct_draft_registration_creates_no_person_or_application(client, db):
    row = db.get(Call, CALL)
    row.publication_state = 'draft'
    db.commit()
    persons = db.scalar(select(func.count()).select_from(Person))
    applications = db.scalar(select(func.count()).select_from(Application))
    sequence = row.next_seq
    for target in (CALL, 'UNKNOWN'):
        response = client.post('/api/v1/applications', json=new_application(call_id=target))
        assert response.status_code == 404 and response.json()['code'] == 'public_course_not_found'
    assert db.scalar(select(func.count()).select_from(Person)) == persons
    assert db.scalar(select(func.count()).select_from(Application)) == applications
    db.refresh(row)
    assert row.next_seq == sequence


def test_publishing_allows_registration_and_withdrawal_blocks_future_submissions(client):
    admin = login(client, ADMIN)
    path = '/api/v1/calls/' + CALL + '/publication'
    state = client.get(path, headers=admin).json()
    first = client.post('/api/v1/applications', json=new_application(email='before-withdrawal@example.test'))
    assert first.status_code == 201
    withdrawn = client.put(path, headers=admin, json={'state': 'draft', 'expected_version': state['version']})
    assert withdrawn.status_code == 200
    assert client.post('/api/v1/applications', json=new_application(email='after-withdrawal@example.test')).status_code == 404
    restored = client.put(path, headers=admin, json={'state': 'published', 'expected_version': withdrawn.json()['version']})
    assert restored.status_code == 200
    assert client.post('/api/v1/applications', json=new_application(email='after-restoration@example.test')).status_code == 201
