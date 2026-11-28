import hashlib
import hmac

import pytest

from app.modules.zoom.client import meeting_settings
from app.modules.zoom.webhooks import validation_response, verify_signature


def test_authentication_modes():
    assert meeting_settings("open") == {"meeting_authentication": False}
    assert meeting_settings("authenticated") == {"meeting_authentication": True}
    assert meeting_settings("institutional", "profile") == {
        "meeting_authentication": True, "authentication_option": "profile"
    }
    with pytest.raises(ValueError):
        meeting_settings("institutional")


def test_webhook_signature():
    body = b'{"event":"meeting.ended"}'
    signature = "v0=" + hmac.new(b"secret", b"v0:1000:" + body, hashlib.sha256).hexdigest()
    assert verify_signature("secret", "1000", signature, body, now=1001)
    assert not verify_signature("secret", "1000", signature, body + b" ", now=1001)
    assert not verify_signature("secret", "1000", signature, body, now=1301)
    assert not verify_signature("secret", "invalid", signature, body, now=1001)
    assert not verify_signature("secret", "1000", "bad", body, now=1001)


def test_validation_response():
    expected = hmac.new(b"secret", b"challenge", hashlib.sha256).hexdigest()
    assert validation_response("secret", "challenge") == {
        "plainToken": "challenge", "encryptedToken": expected
    }


@pytest.mark.parametrize("now,accepted", [(700, True), (699, False), (1300, True), (1301, False)])
def test_webhook_timestamp_window(now, accepted):
    body = b'{"event":"meeting.ended"}'
    signature = "v0=" + hmac.new(b"secret", b"v0:1000:" + body, hashlib.sha256).hexdigest()
    assert verify_signature("secret", "1000", signature, body, now=now) is accepted


@pytest.mark.parametrize("timestamp", ["", "-1000", "1.0", "１０００", "1234567890123"])
def test_webhook_rejects_malformed_timestamp(timestamp):
    assert not verify_signature("secret", timestamp, "v0=" + "0" * 64, b"{}", now=1000)


@pytest.mark.parametrize("secret,token", [("", "challenge"), ("secret", "")])
def test_validation_requires_secret_and_token(secret, token):
    with pytest.raises(ValueError):
        validation_response(secret, token)
