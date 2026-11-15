"""YO9 · Read-only GitHub consumer. No network: every call goes through a fake transport."""

import json

import pytest
from pydantic import SecretStr

from app.modules.integrations.github import (
    GithubApiError,
    GithubAuthError,
    GithubNotFound,
    GithubRateLimited,
    GithubReadOnlyClient,
    InvalidGithubUrl,
    fetch_portfolio_snapshot,
    parse_github_url,
)
from app.modules.integrations.github.client import HttpRequest, HttpResponse
from app.modules.integrations.github.config import GithubSettings

REPO = {
    "full_name": "coder-01/portfolio",
    "html_url": "https://github.com/coder-01/portfolio",
    "description": "Synthetic portfolio",
    "language": "Python",
    "default_branch": "main",
    "fork": False,
    "archived": False,
    "pushed_at": "2026-11-10T09:30:00Z",
}
COMMITS = [{"commit": {"committer": {"date": "2026-11-10T09:30:00Z"}}}, {"commit": {"committer": {"date": "2026-11-09T18:00:00Z"}}}]


class FakeGithub:
    """Records requests and answers from a {path: (status, json, headers)} table."""

    def __init__(self, routes: dict[str, tuple[int, object, dict[str, str]]]):
        self.routes = routes
        self.requests: list[HttpRequest] = []

    def __call__(self, request: HttpRequest) -> HttpResponse:
        self.requests.append(request)
        path = request.url.removeprefix("https://api.github.com").split("?")[0]
        status, payload, headers = self.routes.get(path, (404, {"message": "Not Found"}, {}))
        return HttpResponse(status, headers, json.dumps(payload).encode())


def client_for(routes, token: str | None = None) -> tuple[GithubReadOnlyClient, FakeGithub]:
    fake = FakeGithub(routes)
    return GithubReadOnlyClient(token=SecretStr(token) if token else None, transport=fake), fake


# ---------- links ----------


@pytest.mark.parametrize(
    "raw, owner, repo",
    [
        ("https://github.com/coder-01", "coder-01", None),
        ("https://github.com/coder-01/", "coder-01", None),
        ("https://github.com/coder-01/portfolio", "coder-01", "portfolio"),
        ("https://github.com/coder-01/portfolio.git", "coder-01", "portfolio"),
        ("http://www.github.com/coder-01/portfolio/tree/main/src", "coder-01", "portfolio"),
        ("  https://github.com/coder-01/my.repo_2  ", "coder-01", "my.repo_2"),
    ],
)
def test_parse_valid_links(raw, owner, repo):
    target = parse_github_url(raw)
    assert (target.owner, target.repo) == (owner, repo)


@pytest.mark.parametrize(
    "raw",
    [
        "https://evil.example/coder-01/portfolio",
        "https://github.com.evil.example/coder-01/portfolio",
        "https://user:pw@github.com/coder-01",
        "https://github.com:8443/coder-01",
        "ftp://github.com/coder-01",
        "javascript:alert(1)",
        "https://github.com/",
        "https://github.com/-bad/portfolio",
        "https://github.com/coder-01/..",
        "https://github.com/coder-01/portfolio/extra/segments",
        "github.com/coder-01",
    ],
)
def test_parse_rejects_unsafe_or_malformed_links(raw):
    with pytest.raises(InvalidGithubUrl):
        parse_github_url(raw)


# ---------- client: read-only, token handling ----------


def test_client_sends_only_get_with_headers_and_bearer_token():
    client, fake = client_for({"/repos/o/r": (200, REPO, {})}, token="s3cret-token")
    client.get_json("/repos/o/r")
    (req,) = fake.requests
    assert req.method == "GET"
    assert req.url == "https://api.github.com/repos/o/r"
    assert req.headers["Authorization"] == "Bearer s3cret-token"
    assert req.headers["Accept"] == "application/vnd.github+json"


def test_client_without_token_sends_no_authorization_header():
    client, fake = client_for({"/repos/o/r": (200, REPO, {})})
    client.get_json("/repos/o/r")
    assert "Authorization" not in fake.requests[0].headers


def test_token_never_appears_in_repr_or_str():
    client, _ = client_for({}, token="s3cret-token")
    assert "s3cret-token" not in repr(client) and "s3cret-token" not in str(client)
    assert "s3cret-token" not in repr(GithubSettings(token=SecretStr("s3cret-token")))


@pytest.mark.parametrize("path", ["/user", "/orgs/x", "/repos/o/r/../../user", "/repos/o/r?x=1", "https://evil.example/repos/o/r", "repos/o/r"])
def test_client_rejects_paths_outside_the_read_only_allowlist(path):
    client, fake = client_for({})
    with pytest.raises(GithubApiError):
        client.get_json(path)
    assert fake.requests == []


@pytest.mark.parametrize(
    "status, headers, error",
    [
        (404, {}, GithubNotFound),
        (401, {}, GithubAuthError),
        (403, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1788000000"}, GithubRateLimited),
        (429, {}, GithubRateLimited),
        (500, {}, GithubApiError),
        (403, {}, GithubApiError),
    ],
)
def test_error_statuses_map_to_typed_errors(status, headers, error):
    client, _ = client_for({"/repos/o/r": (status, {"message": "x"}, headers)})
    with pytest.raises(error):
        client.get_json("/repos/o/r")


def test_rate_limit_error_carries_reset_time():
    client, _ = client_for({"/repos/o/r": (403, {}, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1788000000"})})
    with pytest.raises(GithubRateLimited) as info:
        client.get_json("/repos/o/r")
    assert info.value.reset_at == 1788000000


def test_non_json_body_is_an_api_error():
    def transport(_):
        return HttpResponse(200, {}, b"<html>oops</html>")

    with pytest.raises(GithubApiError):
        GithubReadOnlyClient(transport=transport).get_json("/repos/o/r")


# ---------- snapshots ----------


def test_repository_snapshot_keeps_only_minimal_fields():
    client, fake = client_for(
        {
            "/repos/coder-01/portfolio": (200, REPO, {}),
            "/repos/coder-01/portfolio/commits": (200, COMMITS, {}),
            "/repos/coder-01/portfolio/readme": (200, {"name": "README.md"}, {}),
        }
    )
    snap = fetch_portfolio_snapshot("https://github.com/coder-01/portfolio", client)
    assert snap.kind == "repository"
    assert snap.full_name == "coder-01/portfolio"
    assert snap.primary_language == "Python"
    assert snap.has_readme is True
    assert snap.recent_commit_count == 2
    assert snap.last_commit_at.isoformat() == "2026-11-10T09:30:00+00:00"
    assert all(r.method == "GET" for r in fake.requests)
    dumped = snap.model_dump_json()
    assert "author" not in dumped and "email" not in dumped


def test_repository_without_readme_or_commits():
    client, _ = client_for({"/repos/o/empty": (200, {**REPO, "full_name": "o/empty"}, {}), "/repos/o/empty/commits": (200, [], {})})
    snap = fetch_portfolio_snapshot("https://github.com/o/empty", client)
    assert snap.has_readme is False
    assert snap.recent_commit_count == 0 and snap.last_commit_at is None


def test_profile_snapshot_lists_recent_public_repositories():
    client, fake = client_for(
        {
            "/users/coder-01": (200, {"login": "coder-01", "html_url": "https://github.com/coder-01", "public_repos": 3}, {}),
            "/users/coder-01/repos": (
                200,
                [
                    {"name": "portfolio", "language": "Python", "fork": False, "pushed_at": "2026-11-10T09:30:00Z"},
                    {"name": "fork-of-x", "language": None, "fork": True, "pushed_at": None},
                ],
                {},
            ),
        }
    )
    snap = fetch_portfolio_snapshot("https://github.com/coder-01", client)
    assert snap.kind == "profile" and snap.public_repo_count == 3
    assert [r.name for r in snap.repositories] == ["portfolio", "fork-of-x"]
    assert "per_page=10" in fake.requests[1].url


def test_missing_repository_raises_not_found():
    client, _ = client_for({})
    with pytest.raises(GithubNotFound):
        fetch_portfolio_snapshot("https://github.com/o/missing", client)


def test_unexpected_payload_shape_is_an_api_error():
    client, _ = client_for({"/repos/o/r": (200, ["not", "an", "object"], {})})
    with pytest.raises(GithubApiError):
        fetch_portfolio_snapshot("https://github.com/o/r", client)


def test_invalid_link_never_reaches_the_network():
    client, fake = client_for({})
    with pytest.raises(InvalidGithubUrl):
        fetch_portfolio_snapshot("https://evil.example/o/r", client)
    assert fake.requests == []
