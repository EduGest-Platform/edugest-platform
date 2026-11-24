"""Render model-only ERD/dictionary deterministically; never connect to a database."""
import argparse
from pathlib import Path
import sys

from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.dialects import postgresql


def cell(value) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


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
        "Los marcadores muestran nulabilidad y unicidad simple; no inferir restricciones de negocio compuestas. / Markers describe nullability and single-column uniqueness, not composite business constraints.", "", "```mermaid", "erDiagram",
    ]
    for table in tables:
        lines.append(f"    {table.name} {{")
        for column in table.primary_key.columns:
            lines.append(f"        string {column.name} PK")
        lines.append("    }")
    for table in tables:
        for fk in sorted(table.foreign_keys, key=lambda item: (item.parent.name, item.target_fullname)):
            column = fk.parent
            single_primary_key = len(table.primary_key.columns) == 1 and column.primary_key
            unique = single_primary_key or column.unique or any(
                isinstance(c, UniqueConstraint) and list(c.columns) == [column] for c in table.constraints
            )
            left = "|o" if column.nullable else "||"
            right = "o|" if unique else "o{"
            lines.append(f"    {fk.column.table.name} {left}--{right} {table.name} : {column.name}")
    lines += ["```", "", "## Campos y estados almacenados / Fields and stored states", "",
              "Las restricciones CHECK conservan el vocabulario real de estados. Las reglas de transición y autorización viven en servicios y routers, no en este diagrama.",
              "CHECK constraints preserve the stored state vocabulary. Transition/authorization rules live in services and routers, not this diagram.", ""]
    for table in tables:
        lines += [f"### {table.name}", "", "| Campo / Field | PostgreSQL type | Nulo / Nullable | Referencia / Reference |",
                  "|---|---|---|---|"]
        for column in table.columns:
            references = ", ".join(sorted(fk.target_fullname for fk in column.foreign_keys)) or "—"
            lines.append(f"| {column.name} | {cell(column.type.compile(dialect=postgresql.dialect()))} | {'sí / yes' if column.nullable else 'no'} | {references} |")
        for constraint in sorted(table.constraints, key=lambda item: (
            type(item).__name__, item.name or "", tuple(item.columns.keys()), str(getattr(item, 'sqltext', ''))
        )):
            if isinstance(constraint, CheckConstraint):
                lines.append(f"\n- CHECK `{constraint.name}`: `{cell(constraint.sqltext)}`")
            elif isinstance(constraint, UniqueConstraint):
                lines.append(f"\n- UNIQUE `{constraint.name or 'unnamed'}`: `{', '.join(constraint.columns.keys())}`")
        lines.append("")
    lines += ["## Límites / Limits", "",
              "Los tipos del ERD son identificadores esquemáticos; la tabla contiene el tipo PostgreSQL exacto. / ERD field types are schematic; the dictionary provides exact PostgreSQL types.",
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
