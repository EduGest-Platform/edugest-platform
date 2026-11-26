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
