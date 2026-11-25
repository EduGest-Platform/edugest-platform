from tests.conftest import ADMIN, CAPT_DATA, CODER, login
from tests.test_enrollment_documentation_accreditation import admitted_enrollment
from tests.test_enrollment_documentation_reads import own_enrollment, path


def test_accredit_revoke_reaccredit_keeps_immutable_history_and_academic_state(client, db):
    row = admitted_enrollment(client, db)
    admin = login(client, ADMIN)
    for operation, version, expected in [('accredit', 1, 'accredited'), ('revoke', 2, 'pending'), ('accredit', 3, 'accredited')]:
        response = client.post(path(row.id) + '/' + operation, headers=admin, json={'expected_version': version})
        assert response.status_code == 200 and response.json()['state'] == expected
    history = client.get(path(row.id) + '/history', headers=admin).json()
    assert history['total'] == 3
    assert [event['version'] for event in history['items']] == [2, 3, 4]
    assert [event['state'] for event in history['items']] == ['accredited', 'pending', 'accredited']
    assert all(set(event) == {'version', 'state', 'recorded_at'} for event in history['items'])
    paged = client.get(path(row.id) + '/history?limit=1&offset=1', headers=admin).json()
    assert paged['total'] == 3 and paged['items'][0]['version'] == 3
    db.refresh(row)
    assert row.estado == 'activa'


def test_owner_has_no_fabricated_legacy_history_and_foreign_staff_are_denied(client, db):
    row = own_enrollment(db)
    response = client.get(path(row.id) + '/history', headers=login(client, CODER))
    assert response.status_code == 200 and response.json()['items'] == [] and response.json()['total'] == 0
    assert client.get(path(row.id) + '/history', headers=login(client, CAPT_DATA)).status_code == 403
    assert client.get(path(row.id) + '/history?limit=101', headers=login(client, ADMIN)).status_code == 422


def test_revocation_can_correct_an_inactive_enrollment_without_reactivation(client, db):
    row = admitted_enrollment(client, db)
    admin = login(client, ADMIN)
    assert client.post(path(row.id) + '/accredit', headers=admin, json={'expected_version': 1}).status_code == 200
    db.refresh(row)
    row.estado = 'baja_voluntaria'
    db.commit()
    response = client.post(path(row.id) + '/revoke', headers=admin, json={'expected_version': 2})
    assert response.status_code == 200 and response.json()['state'] == 'pending'
    assert response.json()['accredited_at'] is None
    db.refresh(row)
    assert row.estado == 'baja_voluntaria' and row.documentation_accredited_by is None
