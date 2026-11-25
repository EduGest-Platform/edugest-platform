"""Render model-only ERD/dictionary deterministically; never connect to a database."""
import argparse
import json
from pathlib import Path
import re
import sys

from sqlalchemy import CheckConstraint, Column, ForeignKeyConstraint, UniqueConstraint
from sqlalchemy.dialects import postgresql


def cell(value) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def diagram_identifier(value):
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', value):
        raise ValueError(f'Unsupported ERD identifier: {value!r}')
    return value


def diagram_key(column):
    sql_type = str(column.type.compile(dialect=postgresql.dialect()))
    token = re.sub(r'[^A-Za-z0-9_]', '_', sql_type.split('(')[0]).strip('_')
    flags = ','.join(flag for flag, present in [('PK', column.primary_key), ('FK', bool(column.foreign_keys))] if present)
    return f"        {token} {diagram_identifier(column.name)} {flags}"


def sql(expression):
    if hasattr(expression, 'compile'):
        return str(expression.compile(dialect=postgresql.dialect(), compile_kwargs={'literal_binds': True}))
    return str(expression)


def declared_default(column):
    parts = []
    if column.server_default is not None:
        value = getattr(column.server_default, 'arg', None)
        parts.append('server: ' + (sql(value) if value is not None else 'generated / generado'))
    if column.default is not None:
        # Never invoke Python defaults or publish their runtime values.
        parts.append('application (not evaluated / sin evaluar)')
    return '; '.join(parts) or '—'


def state_domains(table):
    """Extract only complete, simple text IN checks; never infer workflow transitions."""
    domains = []
    literal = r"'((?:[^']|'')*)'"
    literals = rf"\s*{literal}(?:\s*,\s*{literal})*\s*"
    for constraint in table.constraints:
        if not isinstance(constraint, CheckConstraint):
            continue
        match = re.fullmatch(r'\s*([A-Za-z_][A-Za-z0-9_]*)\s+IN\s*\((.*)\)\s*', str(constraint.sqltext), re.IGNORECASE | re.DOTALL)
        if match is None or match.group(1) not in table.c or re.fullmatch(literals, match.group(2)) is None:
            continue
        values = [value.replace("''", "'") for value in re.findall(literal, match.group(2))]
        domains.append((match.group(1), constraint.name or 'unnamed', values))
    return sorted(domains, key=lambda item: (item[0], item[1], item[2]))


def globally_unique_columns(table):
    keys = [frozenset(table.primary_key.columns.keys())] if len(table.primary_key.columns) else []
    keys += [frozenset(constraint.columns.keys()) for constraint in table.constraints if isinstance(constraint, UniqueConstraint)]
    for index in table.indexes:
        if (index.unique and index.dialect_options['postgresql'].get('where') is None
                and all(isinstance(expression, Column) for expression in index.expressions)):
            keys.append(frozenset(column.name for column in index.expressions))
    return [key for key in keys if key]


def foreign_key_relations(table):
    """One edge per FK constraint, including composite and self-referencing constraints."""
    for constraint in sorted(table.foreign_key_constraints, key=lambda item: (
            tuple(item.columns.keys()), tuple(element.target_fullname for element in item.elements), item.name or '')):
        local = list(constraint.columns)
        unique = any(key <= frozenset(column.name for column in local) for key in globally_unique_columns(table))
        left = '|o' if any(column.nullable for column in local) else '||'
        right = 'o|' if unique else 'o{'
        label = ','.join(column.name for column in local)
        if len(local) > 1:
            label = f'"{label}"'
        yield f"    {diagram_identifier(constraint.referred_table.name)} {left}--{right} {diagram_identifier(table.name)} : {label}"


def render(metadata) -> str:
    tables = sorted(metadata.tables.values(), key=lambda table: table.name)
    lines = [
        "# ERD y diccionario de datos / ERD and data dictionary", "",
        "Generado desde los modelos SQLAlchemy registrados en [app/models.py](../../api/app/models.py). No consulta bases de datos.",
        "Generated from registered SQLAlchemy metadata. No database connection or live-schema verification occurs.", "",
        "Estado / Status: **CODE_PRESENT_NOT_RUN** para la correspondencia con una base desplegada / for deployed-schema parity.",
        "Regenerar desde `api`: `GISTAR_ENVIRONMENT=local python scripts/export_schema_reference.py`; comprobar con `--check`.",
        "PowerShell: establecer `$env:GISTAR_ENVIRONMENT='local'` antes del mismo comando / set the environment before running it.", "",
        "## Relaciones / Relationships", "",
        "Solo claves foráneas declaradas, sin inferir permisos ni transiciones. / Declared foreign keys only, not permissions or transitions.",
        "Una relación por restricción FK, incluidas las compuestas. Nulabilidad y unicidad global declaradas determinan los marcadores; índices parciales o de expresión no implican unicidad global. / One edge per FK constraint, including composites; markers use declared nullability/global uniqueness, never partial or expression indexes.", "", "```mermaid", "erDiagram",
    ]
    for table in tables:
        lines.append(f"    {diagram_identifier(table.name)} {{")
        for column in table.columns:
            if column.primary_key or column.foreign_keys:
                lines.append(diagram_key(column))
        lines.append("    }")
    for table in tables:
        lines.extend(foreign_key_relations(table))
    lines += ["```", "", "## Dominios textuales declarados / Declared text domains", "",
              "Índice conservador de CHECK completos de la forma `columna IN ('texto', ...)`; no analiza expresiones compuestas ni infiere transiciones, permisos u obligatoriedad de negocio. / Conservative index of complete simple text IN checks, not compound predicates, transitions or permissions.",
              "Las restricciones completas siguen debajo; que un campo no aparezca aquí no implica que no tenga reglas. / Full checks remain below; an omitted field is not necessarily unrestricted.", "",
              "| Tabla / Table | Campo / Field | CHECK | Valores permitidos / Allowed values |", "|---|---|---|---|"]
    for table in tables:
        for column, name, values in state_domains(table):
            lines.append(f"| {table.name} | {column} | {cell(name)} | `{cell(json.dumps(values, ensure_ascii=False))}` |")
    lines += ["", "## Campos y estados almacenados / Fields and stored states", "",
              "Las restricciones CHECK conservan el vocabulario real de estados. Las reglas de transición y autorización viven en servicios y routers, no en este diagrama.",
              "CHECK constraints preserve the stored state vocabulary. Transition/authorization rules live in services and routers, not this diagram.", ""]
    for table in tables:
        lines += [f"### {table.name}", "", "| Campo / Field | PostgreSQL type | Nulo / Nullable | Referencia / Reference | Default declarado / Declared default |",
                  "|---|---|---|---|---|"]
        for column in table.columns:
            references = ", ".join(sorted(fk.target_fullname for fk in column.foreign_keys)) or "—"
            lines.append(f"| {column.name} | {cell(column.type.compile(dialect=postgresql.dialect()))} | {'sí / yes' if column.nullable else 'no'} | {references} | {cell(declared_default(column))} |")
        for constraint in sorted(table.constraints, key=lambda item: (
            type(item).__name__, item.name or "", tuple(item.columns.keys()), str(getattr(item, 'sqltext', '')),
            tuple(element.target_fullname for element in item.elements) if isinstance(item, ForeignKeyConstraint) else (),
            str(getattr(item, 'ondelete', None)), str(getattr(item, 'onupdate', None))
        )):
            if isinstance(constraint, CheckConstraint):
                lines.append(f"\n- CHECK `{constraint.name}`: `{cell(constraint.sqltext)}`")
            elif isinstance(constraint, UniqueConstraint):
                lines.append(f"\n- UNIQUE `{constraint.name or 'unnamed'}`: `{', '.join(constraint.columns.keys())}`")
            elif isinstance(constraint, ForeignKeyConstraint):
                targets = ', '.join(element.target_fullname for element in constraint.elements)
                lines.append(f"\n- FK `{constraint.name or 'unnamed'}`: `({', '.join(constraint.columns.keys())}) -> ({targets})`; "
                             f"ON DELETE `{constraint.ondelete or 'NO ACTION'}`; ON UPDATE `{constraint.onupdate or 'NO ACTION'}`")
        for index in sorted(table.indexes, key=lambda item: (item.name or '', tuple(sql(expression) for expression in item.expressions),
                            bool(item.unique), sql(item.dialect_options['postgresql'].get('where')))):
            expressions = ', '.join(sql(expression) for expression in index.expressions)
            predicate = index.dialect_options['postgresql'].get('where')
            condition = f" WHERE `{cell(sql(predicate))}`" if predicate is not None else ''
            lines.append(f"\n- {'UNIQUE INDEX' if index.unique else 'INDEX'} `{index.name or 'unnamed'}`: `{cell(expressions)}`{condition}")
        lines.append("")
    lines += ["## Límites / Limits", "",
              "Los tipos del ERD son identificadores esquemáticos; la tabla contiene el tipo PostgreSQL exacto. / ERD field types are schematic; the dictionary provides exact PostgreSQL types.",
              "Defaults SQL son expresiones declaradas; defaults Python solo se marcan, nunca se ejecutan. Índices y acciones FK describen metadatos, no un catálogo inspeccionado. / SQL defaults are declared expressions; Python defaults are labelled, never executed. Indexes and FK actions are model metadata, not inspected database objects.",
              "No incluye datos, credenciales, valores de filas ni evidencia de ejecución. No certifica aceptación, permisos, despliegue o ausencia de deriva. Verificar migraciones con PostgreSQL y revisión humana.",
              "No row data, credentials or execution evidence are included. This does not certify acceptance, permissions, deployment or drift absence. Verify migrations against PostgreSQL and obtain human review.", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from app import models  # noqa: F401
    from app.core.db import Base
    output = Path(__file__).resolve().parents[2] / 'docs/data/schema-reference.md'
    content = render(Base.metadata)
    if args.check:
        if not output.is_file() or output.read_text(encoding='utf-8') != content:
            print('Schema reference is missing or stale; regenerate and review it.')
            return 1
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(content, encoding='utf-8', newline='\n')
    print('Schema reference matches registered models; no database was inspected.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
