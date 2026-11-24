"""Offline model/migration parity; does not certify PostgreSQL execution."""
import importlib.util
from pathlib import Path

from sqlalchemy import CheckConstraint, Index, MetaData, Table, UniqueConstraint
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app import models  # noqa: F401
from app.core.db import Base


class RecordingOperations:
    def __init__(self):
        self.metadata = MetaData()
        for table in Base.metadata.sorted_tables:
            if table.name not in {"risk_alert", "intervention"}:
                table.to_metadata(self.metadata)
        self.dropped = []

    def create_table(self, name, *items):
        Table(name, self.metadata, *items)

    def create_index(self, name, table, columns, **options):
        Index(name, *(self.metadata.tables[table].c[column] for column in columns), **options)

    def drop_table(self, name):
        self.dropped.append(name)


def migration():
    path = Path(__file__).resolve().parents[1] / "alembic/versions/0013_risk_evidence.py"
    spec = importlib.util.spec_from_file_location("risk_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.op = RecordingOperations()
    return module


def signature(table):
    return {
        "columns": [(c.name, str(c.type.compile(dialect=postgresql.dialect())), c.nullable,
                     str(c.server_default.arg) if c.server_default is not None else None) for c in table.columns],
        "checks": sorted((c.name, str(c.sqltext)) for c in table.constraints if isinstance(c, CheckConstraint)),
        "unique": sorted((c.name, tuple(c.columns.keys())) for c in table.constraints if isinstance(c, UniqueConstraint)),
        "foreign_keys": sorted((fk.parent.name, fk.target_fullname, fk.ondelete) for fk in table.foreign_keys),
        "indexes": sorted((i.name, tuple(i.columns.keys())) for i in table.indexes),
        "primary_key": tuple(table.primary_key.columns.keys()),
    }


def test_risk_migration_matches_model_and_compiles_for_postgresql():
    module = migration()
    module.upgrade()
    for name in ("risk_alert", "intervention"):
        table = module.op.metadata.tables[name]
        assert signature(table) == signature(Base.metadata.tables[name])
        assert f"CREATE TABLE {name}" in str(CreateTable(table).compile(dialect=postgresql.dialect()))


def test_risk_downgrade_removes_dependent_interventions_first():
    module = migration()
    module.downgrade()
    assert module.op.dropped == ["intervention", "risk_alert"]
