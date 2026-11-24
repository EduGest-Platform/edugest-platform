"""Offline staff migration parity; not a PostgreSQL execution certificate."""
import importlib.util
from pathlib import Path

from app.core.db import Base
from tests.test_risk_migration_contract import RecordingOperations, signature

TABLES = ('staff_profile', 'staff_invitation', 'access_change_request')


def migration():
    path = Path(__file__).resolve().parents[1] / 'alembic/versions/0015_staff_invitations.py'
    spec = importlib.util.spec_from_file_location('staff_migration', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.op = RecordingOperations()
    for name in reversed(TABLES):
        module.op.metadata.remove(module.op.metadata.tables[name])
    return module


def test_staff_migration_matches_every_model_constraint_and_column():
    module = migration()
    module.upgrade()
    for name in TABLES:
        assert signature(module.op.metadata.tables[name]) == signature(Base.metadata.tables[name])


def test_staff_downgrade_preserves_parent_identity_tables():
    module = migration()
    module.downgrade()
    assert module.op.dropped == list(reversed(TABLES))


def test_invitation_schema_has_no_plaintext_secret_column():
    columns = Base.metadata.tables['staff_invitation'].columns.keys()
    assert 'token_hash' in columns
    assert not {'token', 'password', 'access_token'} & set(columns)
