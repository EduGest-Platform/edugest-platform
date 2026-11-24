"""KAN-187: valid inclusive date windows must not silently turn an inverted period into empty metrics."""
from datetime import date

import pytest
from sqlalchemy.dialects import postgresql

from app.core.errors import UserFacingError
from app.modules.attendance.router import _sessions_in


def test_inverted_window_is_rejected_before_querying_any_sessions():
    with pytest.raises(UserFacingError) as error:
        _sessions_in(object(), 'COH-SYN', date(2026, 11, 25), date(2026, 11, 24))
    assert error.value.status_code == 422
    assert error.value.code == 'invalid_date_window'


@pytest.mark.parametrize(('start', 'end'), [
    (None, None), (date(2026, 11, 24), None), (None, date(2026, 11, 24)),
    (date(2026, 11, 24), date(2026, 11, 24)), (date(2026, 11, 24), date(2026, 11, 25)),
])
def test_valid_open_and_closed_windows_keep_inclusive_query_bounds(start, end):
    class QueryRecorder:
        statement = None

        def scalars(self, statement):
            self.statement = statement
            return []

    db = QueryRecorder()
    assert _sessions_in(db, 'COH-SYN', start, end) == []
    sql = str(db.statement.compile(dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}))
    assert "attendance_session.cohort_id = 'COH-SYN'" in sql
    assert ('attendance_session.session_date >=' in sql) is (start is not None)
    assert ('attendance_session.session_date <=' in sql) is (end is not None)
