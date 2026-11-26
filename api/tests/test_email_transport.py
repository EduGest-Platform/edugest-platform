from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pydantic import SecretStr

from app.modules.email.transport import DeliveryError, send_email


def config(**overrides):
    values = dict(
        email_enabled=True,
        email_smtp_host="smtp.example.test",
        email_smtp_port=587,
        email_smtp_security="starttls",
        email_smtp_username=SecretStr("synthetic-user"),
        email_smtp_password=SecretStr("synthetic-password"),
        email_from_address="sender@example.test",
        email_timeout_seconds=15,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def deliver(settings, **overrides):
    values = dict(recipient="student@example.test", subject="Recordatorio", body="Clase de prueba")
    values.update(overrides)
    send_email(settings, **values)


@pytest.mark.parametrize("security,constructor", [("starttls", "SMTP"), ("tls", "SMTP_SSL")])
def test_encrypted_delivery(security, constructor):
    with patch(f"app.modules.email.transport.smtplib.{constructor}") as factory:
        smtp = factory.return_value.__enter__.return_value
        smtp.send_message.return_value = {}
        deliver(config(email_smtp_security=security))
        smtp.login.assert_called_once_with("synthetic-user", "synthetic-password")
        if security == "starttls":
            smtp.starttls.assert_called_once()
            assert [call[0] for call in smtp.method_calls][:4] == ["ehlo", "starttls", "ehlo", "login"]
        else:
            assert factory.call_args.kwargs["context"] is not None
            smtp.starttls.assert_not_called()
        message = smtp.send_message.call_args.args[0]
        assert str(message["To"]) == "student@example.test"
        assert str(message["From"]) == "sender@example.test"
        assert message.get_content().strip() == "Clase de prueba"


@pytest.mark.parametrize("overrides", [
    {"recipient": "student@example.test\nBcc: other@example.test"},
    {"subject": "Subject\r\nBcc: other@example.test"},
    {"subject": ""},
    {"body": ""},
    {"body": "x" * 100001},
])
def test_invalid_message_never_connects(overrides):
    with patch("app.modules.email.transport.smtplib.SMTP") as factory:
        with pytest.raises(ValueError):
            deliver(config(), **overrides)
        factory.assert_not_called()


def test_disabled_never_connects():
    with patch("app.modules.email.transport.smtplib.SMTP") as factory:
        with pytest.raises(DeliveryError, match="disabled"):
            deliver(config(email_enabled=False))
        factory.assert_not_called()


def test_connection_failure_is_sanitized():
    with patch("app.modules.email.transport.smtplib.SMTP", side_effect=OSError("synthetic-password")):
        with pytest.raises(DeliveryError) as exc:
            deliver(config())
        assert "synthetic-password" not in str(exc.value)


def test_tls_failure_never_authenticates():
    with patch("app.modules.email.transport.smtplib.SMTP") as factory:
        smtp = factory.return_value.__enter__.return_value
        smtp.starttls.side_effect = OSError("TLS unavailable")
        with pytest.raises(DeliveryError):
            deliver(config())
        smtp.login.assert_not_called()
        smtp.send_message.assert_not_called()


def test_refused_recipient_is_not_success():
    with patch("app.modules.email.transport.smtplib.SMTP") as factory:
        smtp = factory.return_value.__enter__.return_value
        smtp.send_message.return_value = {"student@example.test": (550, b"Rejected")}
        with pytest.raises(DeliveryError, match="Recipient rejected"):
            deliver(config())


def test_multipart_delivery():
    from app.modules.email.templates import academic_notification

    rendered = academic_notification(topic="Clase <A>")
    with patch("app.modules.email.transport.smtplib.SMTP") as factory:
        smtp = factory.return_value.__enter__.return_value
        smtp.send_message.return_value = {}
        deliver(config(), subject=rendered.subject, body=rendered.text, html_body=rendered.html)
        message = smtp.send_message.call_args.args[0]
        assert message.get_content_type() == "multipart/alternative"
        plain, html = list(message.iter_parts())
        assert plain.get_content_type() == "text/plain"
        assert html.get_content_type() == "text/html"
        assert plain.get_content().strip() == rendered.text
        assert html.get_content().strip() == rendered.html
        assert "&lt;A&gt;" in html.get_content()


@pytest.mark.parametrize("html", ["", "   ", "x" * 100001])
def test_invalid_html_never_connects(html):
    with patch("app.modules.email.transport.smtplib.SMTP") as factory:
        with pytest.raises(ValueError, match="Invalid HTML"):
            deliver(config(), html_body=html)
        factory.assert_not_called()
