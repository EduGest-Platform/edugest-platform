from app.modules.catalog.models import Call
from tests.conftest import ADMIN, login

CALL = 'CONV-IA-2027A'
BASE = '/api/v1/public/courses'


def test_public_list_and_counts_exclude_drafts_even_for_admin(client, db):
    call = db.get(Call, CALL)
    call.publication_state = 'draft'
    db.commit()
    for headers in ({}, login(client, ADMIN)):
        response = client.get(BASE, headers=headers)
        assert response.status_code == 200
        assert response.json()['total'] == 3
        assert CALL not in {row['id'] for row in response.json()['items']}
        draft = client.get(BASE + '/' + CALL, headers=headers)
        missing = client.get(BASE + '/UNKNOWN', headers=headers)
        assert draft.status_code == missing.status_code == 404
        assert draft.json()['code'] == missing.json()['code'] == 'public_course_not_found'


def test_public_projection_filters_and_pagination(client):
    response = client.get(BASE + '?program_id=P-IA&admission_state=abierta&limit=1')
    assert response.status_code == 200
    assert response.json()['total'] == 1
    item = response.json()['items'][0]
    assert item['id'] == CALL
    assert set(item) == {'id', 'program_id', 'program_name', 'name', 'opens_on', 'closes_on', 'capacity', 'admission_state'}
    assert client.get(BASE + '/' + CALL).json() == item
    assert client.get(BASE + '?offset=999').json()['items'] == []
    assert client.get(BASE + '?program_id=UNKNOWN').json() == {'items': [], 'total': 0}


def test_closed_published_offers_remain_visible(client):
    response = client.get(BASE + '?admission_state=cerrada')
    assert response.status_code == 200 and response.json()['total'] == 2
    assert all(row['admission_state'] == 'cerrada' for row in response.json()['items'])
