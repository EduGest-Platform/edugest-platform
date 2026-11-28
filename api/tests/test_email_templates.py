from datetime import datetime, timezone

import pytest

from app.modules.email.templates import academic_notification, academic_reminder, zoom_invitation


START = datetime(2026, 11, 26, 15, 0, tzinfo=timezone.utc)


def test_zoom_invitation():
    url = "https://us02web.zoom.us/j/123456?pwd=abc&x=1"
    result = zoom_invitation(session="Clase", starts_at=START, join_url=url)
    assert result.subject == "Invitación: Clase"
    assert url in result.text
    assert "pwd=abc&amp;x=1" in result.html
    assert "+00:00" in result.text


@pytest.mark.parametrize("url", [
    "http://zoom.us/j/123",
    "https://zoom.us.evil.test/j/123",
    "https://evil.test/j/123",
    "https://user@zoom.us/j/123",
    "https://zoom.us:444/j/123",
    "https://zoom.us/s/123",
    "https://zoom.us/j/123\n",
])
def test_reject_unsafe_zoom_url(url):
    with pytest.raises(ValueError):
        zoom_invitation(session="Clase", starts_at=START, join_url=url)


def test_reminder_requires_timezone():
    with pytest.raises(ValueError):
        academic_reminder(activity="Entrega", due_at=START.replace(tzinfo=None))


def test_html_escapes_untrusted_labels():
    result = academic_notification(topic="<script>alert(1)</script>")
    assert "<script>" not in result.html
    assert "&lt;script&gt;" in result.html
    assert "<script>" in result.text


@pytest.mark.parametrize("label", ["", "a\nb", "x" * 121])
def test_invalid_labels(label):
    with pytest.raises(ValueError):
        academic_notification(topic=label)


def test_reminder():
    result = academic_reminder(activity="Entrega", due_at=START)
    assert result.subject == "Recordatorio: Entrega"
    assert "2026-11-26" in result.text
    assert "EduGest" in result.html
