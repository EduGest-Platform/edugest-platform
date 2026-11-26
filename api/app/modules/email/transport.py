"""Single-recipient SMTP transport. Callers enforce authorization and delivery policy."""
import smtplib
import ssl
from email.headerregistry import Address
from email.message import EmailMessage

from app.core.config import Settings


class DeliveryError(RuntimeError):
    """Delivery failed or its outcome is unknown; do not blindly retry."""


class TransientPreSendError(DeliveryError):
    """Temporary failure before message submission; safe to retry."""


def _address(value: str) -> Address:
    if any(c in value for c in "\r\n"):
        raise ValueError("Invalid email address")
    address = Address(addr_spec=value)
    if not address.username or not address.domain:
        raise ValueError("Invalid email address")
    return address


def send_email(config: Settings, *, recipient: str, subject: str, body: str, html_body: str | None = None) -> None:
    if not config.email_enabled:
        raise DeliveryError("Email integration disabled")
    if not config.email_smtp_host or not config.email_from_address or not config.email_smtp_username or not config.email_smtp_password:
        raise DeliveryError("Email configuration incomplete")
    if not subject.strip() or len(subject) > 200 or any(c in subject for c in "\r\n"):
        raise ValueError("Invalid email subject")
    if not body.strip() or len(body.encode("utf-8")) > 100000:
        raise ValueError("Invalid email body")
    if html_body is not None and (not html_body.strip() or len(html_body.encode("utf-8")) > 100000):
        raise ValueError("Invalid HTML email body")
    message = EmailMessage()
    message["From"] = _address(config.email_from_address)
    message["To"] = _address(recipient)
    message["Subject"] = subject
    message.set_content(body)
    # HTML must come from trusted, escaped institutional templates.
    if html_body is not None:
        message.add_alternative(html_body, subtype="html")
    context = ssl.create_default_context()
    options = {"host": config.email_smtp_host, "port": config.email_smtp_port,
               "timeout": config.email_timeout_seconds}
    submission_started = False
    try:
        if config.email_smtp_security == "tls":
            connection = smtplib.SMTP_SSL(**options, context=context)
        else:
            connection = smtplib.SMTP(**options)
        with connection as smtp:
            if config.email_smtp_security == "starttls":
                smtp.ehlo()
                smtp.starttls(context=context)
                smtp.ehlo()
            smtp.login(config.email_smtp_username.get_secret_value(),
                       config.email_smtp_password.get_secret_value())
            submission_started = True
            refused = smtp.send_message(message)
            if refused:
                raise DeliveryError("Recipient rejected")
    except (OSError, smtplib.SMTPException) as exc:
        if not submission_started and (
            isinstance(exc, (TimeoutError, ConnectionError))
            or isinstance(exc, smtplib.SMTPResponseException) and 400 <= exc.smtp_code < 500
        ):
            raise TransientPreSendError("Temporary SMTP connection failure") from None
        raise DeliveryError("SMTP delivery failed; outcome may be unknown") from None
