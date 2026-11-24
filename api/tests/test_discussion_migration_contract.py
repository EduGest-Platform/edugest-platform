"""Offline discussion migration parity and same-thread parent structure."""
import importlib.util
from pathlib import Path

from app.core.db import Base
from tests.test_risk_migration_contract import RecordingOperations, signature

TABLES = ('discussion_thread', 'discussion_comment')


def migration():
    path = Path(__file__).resolve().parents[1] / 'alembic/versions/0016_scoped_discussions.py'
    spec = importlib.util.spec_from_file_location('discussion_migration', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.op = RecordingOperations()
    for name in reversed(TABLES):
        module.op.metadata.remove(module.op.metadata.tables[name])
    return module


def test_discussion_migration_matches_models():
    module = migration()
    module.upgrade()
    for name in TABLES:
        assert signature(module.op.metadata.tables[name]) == signature(Base.metadata.tables[name])


def test_replies_use_a_composite_foreign_key_to_the_same_thread():
    parent = next(fk for fk in Base.metadata.tables['discussion_comment'].foreign_key_constraints if fk.name == 'fk_discussion_comment_parent_thread')
    assert list(parent.columns.keys()) == ['thread_id', 'parent_id']
    assert [element.target_fullname for element in parent.elements] == ['discussion_comment.thread_id', 'discussion_comment.id']


def test_downgrade_removes_comments_before_threads():
    module = migration()
    module.downgrade()
    assert module.op.dropped == ['discussion_comment', 'discussion_thread']
