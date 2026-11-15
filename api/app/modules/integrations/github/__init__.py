"""Read-only GitHub consumer for portfolio links (YO9).

It never writes to GitHub, never stores the token and only calls api.github.com.
Persistence (PortfolioLink) and HTTP routes are added once migration 0003 and the contract exist.
"""

from app.modules.integrations.github.client import (
    GithubApiError,
    GithubAuthError,
    GithubNotFound,
    GithubRateLimited,
    GithubReadOnlyClient,
    GithubUnavailable,
)
from app.modules.integrations.github.schemas import ProfileSnapshot, RepositorySnapshot
from app.modules.integrations.github.service import fetch_portfolio_snapshot
from app.modules.integrations.github.urls import InvalidGithubUrl, parse_github_url

__all__ = [
    "GithubApiError",
    "GithubAuthError",
    "GithubNotFound",
    "GithubRateLimited",
    "GithubReadOnlyClient",
    "GithubUnavailable",
    "InvalidGithubUrl",
    "ProfileSnapshot",
    "RepositorySnapshot",
    "fetch_portfolio_snapshot",
    "parse_github_url",
]
