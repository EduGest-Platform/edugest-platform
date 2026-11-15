"""Turn a portfolio link into a small, read-only snapshot."""

from datetime import datetime
from typing import Any

from app.modules.integrations.github.client import GithubApiError, GithubReadOnlyClient
from app.modules.integrations.github.schemas import ProfileSnapshot, RepositorySnapshot, RepositorySummary
from app.modules.integrations.github.urls import parse_github_url

COMMIT_SAMPLE_SIZE = 30
PROFILE_REPO_LIMIT = 10


def _when(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _expect(data: Any, kind: type) -> Any:
    if not isinstance(data, kind):
        raise GithubApiError("Unexpected GitHub payload shape")
    return data


def fetch_portfolio_snapshot(url: str, client: GithubReadOnlyClient) -> RepositorySnapshot | ProfileSnapshot:
    """Read-only. Raises InvalidGithubUrl for bad links and GithubError subclasses for API problems."""
    target = parse_github_url(url)
    if target.repo is None:
        return _profile(target.owner, client)
    return _repository(target.owner, target.repo, client)


def _repository(owner: str, repo: str, client: GithubReadOnlyClient) -> RepositorySnapshot:
    base = f"/repos/{owner}/{repo}"
    info = _expect(client.get_json(base), dict)
    commits = _expect(client.get_json(f"{base}/commits", {"per_page": COMMIT_SAMPLE_SIZE}), list)
    last_commit = None
    if commits:
        last_commit = _when(commits[0].get("commit", {}).get("committer", {}).get("date"))
    return RepositorySnapshot(
        full_name=info["full_name"],
        html_url=info["html_url"],
        description=info.get("description"),
        primary_language=info.get("language"),
        default_branch=info["default_branch"],
        is_fork=bool(info.get("fork")),
        is_archived=bool(info.get("archived")),
        has_readme=client.exists(f"{base}/readme"),
        last_push_at=_when(info.get("pushed_at")),
        recent_commit_count=len(commits),
        last_commit_at=last_commit,
    )


def _profile(owner: str, client: GithubReadOnlyClient) -> ProfileSnapshot:
    user = _expect(client.get_json(f"/users/{owner}"), dict)
    repos = _expect(
        client.get_json(f"/users/{owner}/repos", {"per_page": PROFILE_REPO_LIMIT, "sort": "pushed", "type": "owner"}),
        list,
    )
    return ProfileSnapshot(
        login=user["login"],
        html_url=user["html_url"],
        public_repo_count=int(user.get("public_repos", 0)),
        repositories=[
            RepositorySummary(
                name=r["name"],
                primary_language=r.get("language"),
                is_fork=bool(r.get("fork")),
                last_push_at=_when(r.get("pushed_at")),
            )
            for r in repos
        ],
    )
