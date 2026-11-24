"""KAN-126: page boundaries must preserve ordering, filtered totals and authorization scope."""
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.modules.admissions.models import Application
from app.modules.catalog.models import Call
from tests.conftest import CAPT_IA, login


def page(client, headers, **query):
    response = client.get('/api/v1/applications', headers=headers, params=query)
    assert response.status_code == 200, response.text
    return response.json()


def test_equal_timestamps_do_not_duplicate_or_skip_scoped_pages(client, db):
    rows = list(db.scalars(select(Application).join(Call, Call.id == Application.call_id).where(Call.program_id == 'P-IA')))
    assert len(rows) > 3
    for row in rows:
        row.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    db.commit()
    headers = login(client, CAPT_IA)
    expected = [str(row.id) for row in sorted(rows, key=lambda item: item.codigo, reverse=True)]
    seen = []
    for offset in range(0, len(expected), 3):
        result = page(client, headers, limit=3, offset=offset)
        assert result['total'] == len(expected)
        assert all(item['program_id'] == 'P-IA' for item in result['items'])
        seen.extend(item['id'] for item in result['items'])
    assert seen == expected
    assert len(seen) == len(set(seen))


def test_offset_beyond_end_keeps_total_but_never_leaks_foreign_rows(client):
    headers = login(client, CAPT_IA)
    first = page(client, headers, limit=1)
    empty = page(client, headers, limit=1, offset=first['total'])
    assert empty == {'items': [], 'total': first['total']}
    foreign = page(client, headers, call_id='CONV-DATA-2027A', limit=1, offset=0)
    assert foreign == {'items': [], 'total': 0}


def test_search_and_stage_filter_totals_are_independent_of_page_size(client):
    headers = login(client, CAPT_IA)
    item = page(client, headers, limit=1)['items'][0]
    result = page(client, headers, q=item['codigo'], stage=item['stage'], limit=1)
    assert result['total'] == 1 and result['items'][0]['id'] == item['id']
    assert page(client, headers, q=item['codigo'], stage=item['stage'], limit=1, offset=1) == {'items': [], 'total': 1}


@pytest.mark.parametrize('query', [{'limit': 0}, {'limit': 201}, {'offset': -1}, {'q': 'x' * 81}, {'stage': 'invented'}])
def test_invalid_page_parameters_fail_validation(client, query):
    assert client.get('/api/v1/applications', headers=login(client, CAPT_IA), params=query).status_code == 422
