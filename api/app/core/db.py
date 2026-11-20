from collections.abc import Iterator
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings

# Fail fast when PostgreSQL is unreachable instead of waiting for the OS TCP timeout
# (about two minutes on Windows), so /health answers 503 in seconds.
# Five seconds leaves margin for a remote managed database.
DATABASE_CONNECT_TIMEOUT_SECONDS = 5

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"connect_timeout": DATABASE_CONNECT_TIMEOUT_SECONDS},
)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def get_db() -> Iterator[Session]:
    with SessionLocal() as db:
        yield db
