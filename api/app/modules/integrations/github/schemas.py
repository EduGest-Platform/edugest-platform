"""What we keep from GitHub. Data minimisation: no author logins, e-mails or commit messages."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class RepositorySnapshot(BaseModel):
    kind: Literal["repository"] = "repository"
    full_name: str
    html_url: str
    description: str | None
    primary_language: str | None
    default_branch: str
    is_fork: bool
    is_archived: bool
    has_readme: bool
    last_push_at: datetime | None
    recent_commit_count: int  # commits in the sampled page (at most `commit_sample_size`)
    last_commit_at: datetime | None


class RepositorySummary(BaseModel):
    name: str
    primary_language: str | None
    is_fork: bool
    last_push_at: datetime | None


class ProfileSnapshot(BaseModel):
    kind: Literal["profile"] = "profile"
    login: str
    html_url: str
    public_repo_count: int
    repositories: list[RepositorySummary]  # most recently pushed first, capped
