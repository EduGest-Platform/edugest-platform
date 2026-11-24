"""Offline stale-write and tombstone output regressions."""
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.core.errors import UserFacingError
from app.modules.discussions.service import comment_out, require_version


def test_tombstone_never_serializes_retained_body():
    row = SimpleNamespace(id=uuid.uuid4(), thread_id=uuid.uuid4(), parent_id=None, actor_user_id=uuid.uuid4(),
                          body='Synthetic retained text', version=2, created_at=datetime.now(timezone.utc), edited_at=None,
                          deleted_at=datetime.now(timezone.utc))
    result = comment_out(row)
    assert result.body is None
    assert row.body == 'Synthetic retained text'
    assert 'Synthetic retained text' not in result.model_dump_json()


@pytest.mark.parametrize(('current', 'expected', 'kind'), [(2, 1, 'comment'), (3, 2, 'thread')])
def test_old_versions_cannot_overwrite_new_revisions(current, expected, kind):
    with pytest.raises(UserFacingError) as error:
        require_version(current, expected, kind)
    assert error.value.status_code == 409 and error.value.code == f'stale_{kind}'


def test_matching_version_is_accepted():
    require_version(3, 3, 'comment')
