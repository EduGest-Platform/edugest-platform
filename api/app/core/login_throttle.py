"""Brute-force protection for /auth/login: after N failed attempts for the same account (or the same client) inside a
window, further attempts get 429 until the window passes. A successful login clears the account's counter.

In memory on purpose: the demo runs one API process. With several instances this must move to the database or a
shared cache (documented in api/README.md). Keys are SHA-256 digests, so no e-mail or IP is kept in clear.
"""

import hashlib
import threading
import time
from collections import defaultdict, deque

from app.core.config import settings

_failures: dict[str, deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def _key(kind: str, value: str) -> str:
    return kind + ":" + hashlib.sha256(value.lower().encode("utf-8")).hexdigest()


def _keys(email: str, client: str | None) -> list[str]:
    keys = [_key("account", email)] if email else []
    if client:
        keys.append(_key("client", client))
    return keys


def _recent(key: str, now: float) -> deque[float]:
    window = settings.login_window_minutes * 60
    attempts = _failures[key]
    while attempts and now - attempts[0] > window:
        attempts.popleft()
    return attempts


def retry_after_seconds(email: str, client: str | None) -> int:
    """0 when the attempt may go ahead; otherwise how many seconds until the oldest counted failure expires."""
    now = time.monotonic()
    window = settings.login_window_minutes * 60
    limits = {"account": settings.login_max_failures, "client": settings.login_max_failures * 4}
    with _lock:
        waits = [
            int(window - (now - attempts[0])) + 1
            for key in _keys(email, client)
            if len(attempts := _recent(key, now)) >= limits[key.split(":", 1)[0]]
        ]
    return max(waits, default=0)


def record_failure(email: str, client: str | None) -> None:
    now = time.monotonic()
    with _lock:
        for key in _keys(email, client):
            _recent(key, now).append(now)


def record_success(email: str) -> None:
    with _lock:
        _failures.pop(_key("account", email), None)


def reset() -> None:
    """Test helper: forget every counter."""
    with _lock:
        _failures.clear()
