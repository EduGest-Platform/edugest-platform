from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Runtime configuration. Every value can be overridden with a GISTAR_* environment variable."""

    # hide_input_in_errors: a rejected secret must not be echoed in startup errors or logs.
    model_config = SettingsConfigDict(
        env_prefix="GISTAR_", env_file=".env", extra="ignore", hide_input_in_errors=True
    )

    environment: Literal["local", "staging", "production"] = "production"
    database_url: str = "postgresql+psycopg://gistar:gistar@localhost:5432/gistar"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8443", "http://localhost:3000"]
    session_ttl_hours: int = 8
    # Login brute-force protection: failed attempts per account inside the window before 429 (4x that per client).
    login_max_failures: int = 5
    login_window_minutes: int = 15
    # Proxies in front of the API that append to X-Forwarded-For (Render: 1). 0 = use the TCP peer, ignore the header.
    trusted_proxy_hops: int = Field(default=0, ge=0, le=5)
    # Synthetic demo accounts only. Never reuse for real people.
    demo_password: str = "gistar-demo-2026"
    # scrypt cost; tests lower it to keep the suite fast.
    scrypt_n: int = 2**14
    # Single source of synthetic data, shared with the web prototype.
    seed_path: str = str(REPO_ROOT / "src" / "gistar" / "seed.json")
    # Synthetic course documents for the RAG knowledge ingest (KAN-130): corpus.json plus one Markdown file per document.
    corpus_path: str = str(REPO_ROOT / "evals" / "rag" / "corpus")
    # RAG embeddings (KAN-130 part B). Off by default, so tests and CI never call the network.
    rag_embed: bool = False
    # Read from GEMINI_API_KEY (no GISTAR_ prefix), the name used across the project. Never printed or logged.
    gemini_api_key: SecretStr | None = Field(default=None, validation_alias="GEMINI_API_KEY")
    # Aggregates for coordination are suppressed below these sizes.
    min_group_size: int = 5
    min_cell_size: int = 3

    @model_validator(mode="after")
    def require_deployment_secrets(self) -> "Settings":
        if self.environment != "local":
            if self.demo_password == "gistar-demo-2026" or len(self.demo_password) < 20:
                raise ValueError("GISTAR_DEMO_PASSWORD must be a unique value of at least 20 characters outside local development")
            if self.database_url == "postgresql+psycopg://gistar:gistar@localhost:5432/gistar":
                raise ValueError("GISTAR_DATABASE_URL must be configured outside local development")
        return self


settings = Settings()
