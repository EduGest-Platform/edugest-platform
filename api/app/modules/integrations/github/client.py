"""Minimal read-only GitHub REST client built on the standard library.

Only GET requests to api.github.com under /repos/ and /users/ are possible. Redirects are never followed.
The transport is injectable, so tests never touch the network.
"""

import json
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlencode

from pydantic import SecretStr

API_BASE = "https://api.github.com"
_ALLOWED_PREFIXES = ("/repos/", "/users/")


class GithubError(Exception):
    """Base class for every GitHub consumer error."""

    code = "github_error"


class GithubNotFound(GithubError):
    """The repository or user does not exist (or is private)."""

    code = "not_found"


class GithubAuthError(GithubError):
    """The token was rejected."""

    code = "auth_error"


class GithubRateLimited(GithubError):
    code = "rate_limited"

    def __init__(self, reset_at: int | None = None):
        super().__init__("GitHub rate limit reached")
        self.reset_at = reset_at  # Unix timestamp when the limit resets, if GitHub said so


class GithubApiError(GithubError):
    """Unexpected status or payload."""

    code = "api_error"


class GithubConflict(GithubApiError):
    """HTTP 409. For the commits endpoint it means the repository is empty."""

    code = "conflict"


class GithubRedirected(GithubApiError):
    """The repository or user moved (3xx). Redirects are never followed; the link must be updated."""

    code = "redirected"

    def __init__(self, location: str | None = None):
        super().__init__("GitHub says this resource moved; update the portfolio link")
        self.location = location


class GithubUnavailable(GithubError):
    """Network failure or timeout."""

    code = "unavailable"


@dataclass(frozen=True)
class HttpRequest:
    method: str
    url: str
    headers: Mapping[str, str]
    timeout: float


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: Mapping[str, str] = field(default_factory=dict)
    body: bytes = b""


Transport = Callable[[HttpRequest], HttpResponse]


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """urllib follows redirects by default and forwards the Authorization header with them.
    Refusing here means the token can only ever reach the host we validated."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D102
        return None


_opener = urllib.request.build_opener(_NoRedirect())


def urllib_transport(request: HttpRequest) -> HttpResponse:
    req = urllib.request.Request(request.url, headers=dict(request.headers), method=request.method)
    try:
        with _opener.open(req, timeout=request.timeout) as resp:  # noqa: S310 (fixed https host)
            return HttpResponse(resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read())
    except urllib.error.HTTPError as exc:
        return HttpResponse(exc.code, {k.lower(): v for k, v in exc.headers.items()}, exc.read())
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise GithubUnavailable("Could not reach GitHub") from exc


class GithubReadOnlyClient:
    def __init__(self, token: SecretStr | None = None, timeout: float = 10.0, transport: Transport = urllib_transport):
        self._token = token
        self._timeout = timeout
        self._transport = transport

    def __repr__(self) -> str:  # never expose the token
        return f"GithubReadOnlyClient(authenticated={self._token is not None})"

    def get_json(self, path: str, params: Mapping[str, str | int] | None = None) -> Any:
        """GET `path` (must start with /repos/ or /users/) and return the decoded JSON body."""
        status, headers, body = self._get(path, params)
        if status >= 300:
            self._raise_for_status(status, headers)
        try:
            return json.loads(body)
        except ValueError as exc:
            raise GithubApiError("GitHub returned a body that is not JSON") from exc

    def exists(self, path: str) -> bool:
        """True when the resource exists, False on 404. Other errors still raise."""
        status, headers, _ = self._get(path, None)
        if status == 404:
            return False
        if status >= 300:
            self._raise_for_status(status, headers)
        return True

    def _get(self, path: str, params: Mapping[str, str | int] | None) -> tuple[int, Mapping[str, str], bytes]:
        if not path.startswith(_ALLOWED_PREFIXES) or ".." in path or "?" in path or "#" in path:
            raise GithubApiError("Path not allowed for the read-only client")
        url = API_BASE + path + (f"?{urlencode(params)}" if params else "")
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "edugest-platform",
        }
        if self._token is not None:
            headers["Authorization"] = f"Bearer {self._token.get_secret_value()}"
        response = self._transport(HttpRequest("GET", url, headers, self._timeout))
        return response.status, response.headers, response.body

    @staticmethod
    def _raise_for_status(status: int, headers: Mapping[str, str]) -> None:
        if 300 <= status < 400:
            raise GithubRedirected(headers.get("location"))
        if status == 409:
            raise GithubConflict("GitHub answered 409 (for commits this means an empty repository)")
        if status == 404:
            raise GithubNotFound("Not found on GitHub")
        if status == 401:
            raise GithubAuthError("GitHub rejected the token")
        if status == 429 or (status == 403 and (headers.get("x-ratelimit-remaining") == "0" or "retry-after" in headers)):
            reset = headers.get("x-ratelimit-reset")
            raise GithubRateLimited(int(reset) if reset and reset.isdigit() else None)
        raise GithubApiError(f"Unexpected GitHub status {status}")
