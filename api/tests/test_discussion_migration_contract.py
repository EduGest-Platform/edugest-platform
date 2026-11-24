"""Offline discussion migration parity and same-thread parent structure."""
import importlib.util
from pathlib import Path
from sqlalchemy import CheckConstraint, ForeignKeyConstraint

from app.core.db import Base
from tests.test_risk_migration_contract import RecordingOperations, signature

TABLES = ('discussion_thread', 'discussion_comment')


class RevisionOperations(RecordingOperations):
    def add_column(self, table, column):
        self.metadata.tables[table].append_column(column)

    def create_check_constraint(self, name, table, condition):
        self.metadata.tables[table].append_constraint(CheckConstraint(condition, name=name))

    def create_foreign_key(self, name, source, target, local, remote):
        self.metadata.tables[source].append_constraint(ForeignKeyConstraint(local, [f'{target}.{column}' for column in remote], name=name))


def migration():
    path = Path(__file__).resolve().parents[1] / 'alembic/versions/0016_scoped_discussions.py'
    spec = importlib.util.spec_from_file_location('discussion_migration', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.op = RevisionOperations()
    for name in reversed(TABLES):
        module.op.metadata.remove(module.op.metadata.tables[name])
    return module


def test_discussion_migration_matches_models():
    module = migration()
    module.upgrade()
    path = Path(__file__).resolve().parents[1] / 'alembic/versions/0017_discussion_revisions.py'
    spec = importlib.util.spec_from_file_location('discussion_revisions', path)
    revisions = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(revisions)
    revisions.op = module.op
    revisions.upgrade()
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
