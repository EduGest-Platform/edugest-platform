import pytest
from pydantic import ValidationError

from app.core.config import Settings

DEFAULT_DATABASE_URL = "postgresql+psycopg://gistar:gistar@localhost:5432/gistar"
CONFIGURED_DATABASE_URL = "postgresql+psycopg://gistar:unique@db:5432/gistar"
CONFIGURED_DEMO_PASSWORD = "unique-demo-password-for-staging"


@pytest.fixture(autouse=True)
def clean_gistar_env(monkeypatch):
    """Settings reads GISTAR_* variables; ignore the ones conftest or the shell may have set."""
    for name in ("GISTAR_ENVIRONMENT", "GISTAR_DEMO_PASSWORD", "GISTAR_DATABASE_URL"):
        monkeypatch.delenv(name, raising=False)


def test_local_demo_defaults_remain_available():
    settings = Settings(_env_file=None, environment="local")
    assert settings.environment == "local"


def test_missing_environment_fails_closed():
    with pytest.raises(ValidationError, match="GISTAR_DEMO_PASSWORD"):
        Settings(_env_file=None)


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_accessible_environment_rejects_default_demo_password(environment):
    with pytest.raises(ValidationError, match="GISTAR_DEMO_PASSWORD"):
        Settings(_env_file=None, environment=environment, database_url=CONFIGURED_DATABASE_URL)


def test_accessible_environment_rejects_short_demo_password():
    with pytest.raises(ValidationError, match="GISTAR_DEMO_PASSWORD"):
        Settings(_env_file=None, environment="staging", database_url=CONFIGURED_DATABASE_URL, demo_password="short")


def test_accessible_environment_rejects_default_database_url():
    with pytest.raises(ValidationError, match="GISTAR_DATABASE_URL"):
        Settings(_env_file=None, environment="staging", demo_password=CONFIGURED_DEMO_PASSWORD)


def test_accessible_environment_accepts_configured_secrets():
    settings = Settings(
        _env_file=None,
        environment="staging",
        database_url=CONFIGURED_DATABASE_URL,
        demo_password=CONFIGURED_DEMO_PASSWORD,
    )
    assert settings.environment == "staging"


def test_rejected_values_are_not_echoed_in_the_error():
    with pytest.raises(ValidationError) as error:
        Settings(_env_file=None, environment="staging", database_url=CONFIGURED_DATABASE_URL, demo_password="short-secret")
    message = str(error.value)
    assert "short-secret" not in message
    assert "gistar:unique@" not in message
