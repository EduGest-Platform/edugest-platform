"""Parse portfolio links. Only the owner and repository names are used to build API calls (no SSRF)."""

import re
from dataclasses import dataclass
from urllib.parse import urlparse

_GITHUB_HOSTS = {"github.com", "www.github.com"}
_OWNER_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
_REPO_RE = re.compile(r"^[A-Za-z0-9._-]{1,100}$")


class InvalidGithubUrl(ValueError):
    """The link is not a GitHub profile or repository URL."""

    code = "invalid_url"


@dataclass(frozen=True)
class GithubTarget:
    owner: str
    repo: str | None  # None means a profile link


def parse_github_url(raw: str) -> GithubTarget:
    parsed = urlparse(raw.strip())
    if parsed.scheme not in {"http", "https"} or (parsed.hostname or "").lower() not in _GITHUB_HOSTS:
        raise InvalidGithubUrl("Only https://github.com/... links are accepted")
    if parsed.port is not None or parsed.username or parsed.password:
        raise InvalidGithubUrl("The link must not contain credentials or a port")

    segments = [s for s in parsed.path.split("/") if s]
    if not segments or len(segments) > 2 and segments[2] not in {"tree", "blob", "commits", "pulls", "issues"}:
        raise InvalidGithubUrl("Expected github.com/<owner> or github.com/<owner>/<repo>")

    owner = segments[0]
    if not _OWNER_RE.fullmatch(owner):
        raise InvalidGithubUrl("Invalid GitHub user or organisation name")
    if len(segments) == 1:
        return GithubTarget(owner=owner, repo=None)

    repo = segments[1].removesuffix(".git")
    if repo in {".", ".."} or not _REPO_RE.fullmatch(repo):
        raise InvalidGithubUrl("Invalid repository name")
    return GithubTarget(owner=owner, repo=repo)
