"""Offline generated-dictionary regressions, without PostgreSQL claims."""
import pytest
from sqlalchemy import CheckConstraint, Column, ForeignKey, ForeignKeyConstraint, Index, Integer, MetaData, String, Table, UniqueConstraint, text

from scripts.export_schema_reference import render, state_domains


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


def test_foreign_key_that_is_the_entire_primary_key_is_unique():
    data = MetaData()
    Table('cohort', data, Column('id', Integer, primary_key=True))
    Table('framework', data, Column('cohort_id', Integer, ForeignKey('cohort.id'), primary_key=True))
    text = render(data)
    assert 'cohort ||--o| framework : cohort_id' in text
    assert 'cohort ||--o{ framework : cohort_id' not in text


def test_individual_columns_of_composite_primary_key_are_not_unique():
    data = MetaData()
    Table('cohort', data, Column('id', Integer, primary_key=True))
    Table('framework', data, Column('cohort_id', Integer, ForeignKey('cohort.id'), primary_key=True),
          Column('version', Integer, primary_key=True))
    text = render(data)
    assert 'cohort ||--o{ framework : cohort_id' in text
    assert 'cohort ||--o| framework : cohort_id' not in text


def test_composite_foreign_key_remains_one_relation_with_tuple_uniqueness():
    data = MetaData()
    Table('parent', data, Column('id', Integer, primary_key=True), Column('version', Integer, primary_key=True))
    Table('child', data, Column('id', Integer, primary_key=True), Column('parent_id', Integer, nullable=False),
          Column('parent_version', Integer, nullable=False),
          ForeignKeyConstraint(['parent_id', 'parent_version'], ['parent.id', 'parent.version']),
          UniqueConstraint('parent_id', 'parent_version'))
    edges = [line for line in render(data).splitlines() if '--' in line and ' child :' in line]
    assert edges == ['    parent ||--o| child : "parent_id,parent_version"']


def test_partial_unique_index_does_not_make_all_foreign_keys_one_to_one():
    data = MetaData()
    Table('parent', data, Column('id', Integer, primary_key=True))
    child = Table('child', data, Column('id', Integer, primary_key=True), Column('parent_id', Integer, ForeignKey('parent.id'), nullable=False),
                  Column('active', Integer))
    index = Index('uq_active_parent', child.c.parent_id, unique=True, postgresql_where=child.c.active == 1)
    assert 'parent ||--o{ child : parent_id' in render(data)
    index.dialect_options['postgresql']['where'] = None
    assert 'parent ||--o| child : parent_id' in render(data)


def test_nullable_composite_self_reference_is_optional_as_a_single_edge():
    data = MetaData()
    Table('comment', data, Column('id', Integer, primary_key=True), Column('thread_id', Integer, nullable=False),
          Column('reply_to_id', Integer), UniqueConstraint('id', 'thread_id'),
          ForeignKeyConstraint(['reply_to_id', 'thread_id'], ['comment.id', 'comment.thread_id']))
    assert 'comment |o--o{ comment : "reply_to_id,thread_id"' in render(data)


def test_diagram_keys_distinguish_integer_primary_keys_and_foreign_keys():
    text = render(metadata())
    assert 'INTEGER id PK' in text
    assert 'INTEGER parent_id FK' in text
    assert 'string id PK' not in text


def test_a_key_can_be_both_primary_and_foreign_without_duplicating_the_field():
    data = MetaData()
    Table('parent', data, Column('id', Integer, primary_key=True))
    Table('child', data, Column('parent_id', Integer, ForeignKey('parent.id'), primary_key=True))
    assert render(data).count('INTEGER parent_id PK,FK') == 1


def test_unsupported_diagram_identifiers_fail_instead_of_injecting_markup():
    data = MetaData()
    Table('unsafe table', data, Column('id', Integer, primary_key=True))
    with pytest.raises(ValueError, match='Unsupported ERD identifier'):
        render(data)


def test_registered_model_diagram_contains_each_foreign_key_constraint_once():
    from app import models  # noqa: F401
    from app.core.db import Base

    text = render(Base.metadata)
    edges = [line for line in text.splitlines() if '--' in line and ' : ' in line]
    assert len(edges) == sum(len(table.foreign_key_constraints) for table in Base.metadata.tables.values())


def test_defaults_are_described_without_executing_python_generators():
    def forbidden_default():
        raise AssertionError('Python defaults must never run during documentation export')

    data = MetaData()
    Table('example', data, Column('id', Integer, primary_key=True, default=forbidden_default),
          Column('state', String(20), server_default='pending'), Column('created_at', String(30), server_default=text('CURRENT_TIMESTAMP')))
    rendered = render(data)
    assert 'application (not evaluated / sin evaluar)' in rendered
    assert 'server: pending' in rendered and 'server: CURRENT_TIMESTAMP' in rendered


def test_partial_unique_index_predicate_and_fk_delete_action_are_visible():
    data = MetaData()
    Table('parent', data, Column('id', Integer, primary_key=True))
    child = Table('child', data, Column('id', Integer, primary_key=True),
                  Column('parent_id', Integer, ForeignKey('parent.id', ondelete='CASCADE')), Column('active', Integer))
    Index('uq_active_parent', child.c.parent_id, unique=True, postgresql_where=child.c.active == 1)
    rendered = render(data)
    assert 'UNIQUE INDEX `uq_active_parent`' in rendered
    assert 'WHERE `child.active = 1`' in rendered
    assert 'ON DELETE `CASCADE`' in rendered


def test_multiple_unnamed_composite_foreign_keys_have_stable_order():
    results = []
    for reverse in (False, True):
        data = MetaData()
        Table('parent', data, Column('a', Integer, primary_key=True), Column('b', Integer, primary_key=True))
        constraints = [ForeignKeyConstraint(['first_a', 'first_b'], ['parent.a', 'parent.b']),
                       ForeignKeyConstraint(['last_a', 'last_b'], ['parent.a', 'parent.b'])]
        Table('child', data, Column('id', Integer, primary_key=True),
              *(Column(name, Integer) for name in ('first_a', 'first_b', 'last_a', 'last_b')),
              *(reversed(constraints) if reverse else constraints))
        results.append(render(data))
    assert results[0] == results[1]


def test_unnamed_foreign_keys_on_the_same_column_sort_by_target():
    results = []
    for targets in (['first.id', 'second.id'], ['second.id', 'first.id']):
        data = MetaData()
        for name in ('first', 'second'):
            Table(name, data, Column('id', Integer, primary_key=True))
        Table('child', data, Column('id', Integer, primary_key=True), Column('parent_id', Integer),
              *(ForeignKeyConstraint(['parent_id'], [target]) for target in targets))
        results.append(render(data))
    assert results[0] == results[1]


def test_text_domains_decode_sql_quotes_without_executing_expressions():
    data = MetaData()
    table = Table('example', data, Column('state', String(30)), CheckConstraint("state IN ('pending', 'it''s reviewed')", name='ck_state'))
    assert state_domains(table) == [('state', 'ck_state', ['pending', "it's reviewed"])]


def test_domain_index_does_not_invent_states_from_compound_or_numeric_checks():
    data = MetaData()
    table = Table('example', data, Column('state', String(30)), Column('count', Integer),
        CheckConstraint("state IN ('pending', 'reviewed') OR state IS NULL", name='ck_compound'),
        CheckConstraint('count IN (1, 2)', name='ck_count'))
    assert state_domains(table) == []
    rendered = render(data)
    assert "state IN ('pending', 'reviewed') OR state IS NULL" in rendered


def test_domain_index_preserves_storage_vocabulary_without_creating_transitions():
    rendered = render(metadata())
    assert '| child | state | ck_state | `["pending", "reviewed"]` |' in rendered
    assert 'not compound predicates, transitions or permissions' in rendered
