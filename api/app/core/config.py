from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """Runtime configuration. Every value can be overridden with a GISTAR_* environment variable."""

    model_config = SettingsConfigDict(env_prefix="GISTAR_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://gistar:gistar@localhost:5432/gistar"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:8443", "http://localhost:3000"]
    session_ttl_hours: int = 8
    # Synthetic demo accounts only. Never reuse for real people.
    demo_password: str = "gistar-demo-2026"
    # scrypt cost; tests lower it to keep the suite fast.
    scrypt_n: int = 2**14
    # Single source of synthetic data, shared with the web prototype.
    seed_path: str = str(REPO_ROOT / "src" / "gistar" / "seed.json")
    # Aggregates for coordination are suppressed below these sizes.
    min_group_size: int = 5
    min_cell_size: int = 3


settings = Settings()
