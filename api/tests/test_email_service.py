from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.modules.email.service import enqueue
from app.modules.email.templates import RenderedEmail

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def payload(**overrides):
    values = dict(idempotency_key="event-1", cohort_id="cohort-1",
                  created_by=uuid4(), recipient="student@example.test",
                  rendered=RenderedEmail("Aviso", "Texto", "<p>Texto</p>"),
                  available_at=NOW)
    values.update(overrides)
    return values


def existing(values):
    data = dict(values)
    rendered = data.pop("rendered")
    return SimpleNamespace(**data, id=uuid4(), subject=rendered.subject,
                           text_body=rendered.text, html_body=rendered.html)


def test_enqueue_new():
    db = MagicMock()
    message_id = uuid4()
    db.execute.return_value.scalar_one_or_none.return_value = message_id
    assert enqueue(db, **payload()) == message_id
    db.scalars.assert_not_called()
    db.commit.assert_not_called()


def test_identical_request_reuses_id():
    db = MagicMock()
    values = payload()
    message = existing(values)
    db.execute.return_value.scalar_one_or_none.return_value = None
    db.scalars.return_value.one.return_value = message
    assert enqueue(db, **values) == message.id


@pytest.mark.parametrize("field,value", [
    ("recipient", "other@example.test"),
    ("cohort_id", "cohort-2"),
    ("subject", "Different"),
    ("created_by", uuid4()),
])
def test_conflicting_request_rejected(field, value):
    db = MagicMock()
    values = payload()
    message = existing(values)
    setattr(message, field, value)
    db.execute.return_value.scalar_one_or_none.return_value = None
    db.scalars.return_value.one.return_value = message
    with pytest.raises(ValueError, match="Idempotency key conflict"):
        enqueue(db, **values)


@pytest.mark.parametrize("overrides", [
    {"idempotency_key": ""},
    {"idempotency_key": "x" * 129},
    {"available_at": datetime(2026, 1, 1)},
    {"recipient": "student@example.test\nBcc: other@example.test"},
    {"rendered": RenderedEmail("", "Texto", "<p>Texto</p>")},
    {"rendered": RenderedEmail("Aviso", "", "<p>Texto</p>")},
    {"rendered": RenderedEmail("Aviso", "Texto", "x" * 100001)},
])
def test_invalid_request_never_inserts(overrides):
    db = MagicMock()
    with pytest.raises(ValueError):
        enqueue(db, **payload(**overrides))
    db.execute.assert_not_called()
