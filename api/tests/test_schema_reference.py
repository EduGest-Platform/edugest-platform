"""Offline generated-dictionary regressions, without PostgreSQL claims."""
from sqlalchemy import CheckConstraint, Column, ForeignKey, Integer, MetaData, String, Table, UniqueConstraint

from scripts.export_schema_reference import render


def metadata(reverse=False):
    result = MetaData()
    definitions = [
        ('parent', [Column('id', Integer, primary_key=True)]),
        ('child', [Column('id', Integer, primary_key=True), Column('parent_id', Integer, ForeignKey('parent.id'), nullable=True, unique=True),
                   Column('state', String(20), nullable=False), CheckConstraint("state IN ('pending', 'reviewed')", name='ck_state')]),
    ]
    for name, columns in reversed(definitions) if reverse else definitions:
        Table(name, result, *columns)
    return result


def test_reference_is_deterministic_and_covers_stored_state_and_foreign_keys():
    rendered = render(metadata())
    assert rendered == render(metadata(reverse=True))
    assert 'parent |o--o| child : parent_id' in rendered
    assert 'parent.id' in rendered
    assert "state IN ('pending', 'reviewed')" in rendered
    assert 'VARCHAR(20)' in rendered
    assert 'No database connection' in rendered


def test_schema_changes_make_the_reference_stale():
    original = metadata()
    before = render(original)
    original.tables['child'].append_column(Column('new_field', Integer))
    assert before != render(original)
    assert '| new_field |' in render(original)


def test_multiple_unnamed_constraints_have_stable_order():
    variants = []
    for names in (['a', 'b'], ['b', 'a']):
        data = MetaData()
        Table('example', data, Column('id', Integer, primary_key=True), Column('a', Integer), Column('b', Integer),
              *(UniqueConstraint(name) for name in names))
        variants.append(render(data))
    assert variants[0] == variants[1]
