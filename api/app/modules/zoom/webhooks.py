"""Verify Zoom webhook signatures before parsing or processing events."""
import hashlib
import hmac
import time


def verify_signature(secret: str, timestamp: str, signature: str, body: bytes,
                     *, now: float | None = None) -> bool:
    if not secret or not timestamp.isascii() or not timestamp.isdecimal() or len(timestamp) > 12:
        return False
    if not signature.isascii() or len(signature) != 67:
        return False
    if abs((time.time() if now is None else now) - int(timestamp)) > 300:
        return False
    message = b"v0:" + timestamp.encode("ascii") + b":" + body
    expected = "v0=" + hmac.new(secret.encode(), message, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def validation_response(secret: str, plain_token: str) -> dict[str, str]:
    if not secret or not plain_token:
        raise ValueError("Missing webhook validation token")
    return {
        "plainToken": plain_token,
        "encryptedToken": hmac.new(secret.encode(), plain_token.encode(), hashlib.sha256).hexdigest(),
    }
