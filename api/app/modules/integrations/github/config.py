from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class GithubSettings(BaseSettings):
    """GitHub consumer configuration. Override with GISTAR_GITHUB_* environment variables."""

    model_config = SettingsConfigDict(env_prefix="GISTAR_GITHUB_", env_file=".env", extra="ignore")

    # Read-only token. Optional: without it GitHub allows only 60 requests per hour.
    token: SecretStr | None = None
    timeout_seconds: float = 10.0
