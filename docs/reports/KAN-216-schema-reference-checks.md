# KAN-216 — Schema reference checks / Comprobaciones de referencia

## EN — Canonical

Jira task KAN-216 is assigned to Elizabeth, due **3 December 2026**. Implementation: Yohanna; sole requested reviewer: Anasfady. This stack extends the existing `api/scripts/export_schema_reference.py`; it does not introduce a parallel schema inventory or modify operational models.

Review/merge order: composite relations → typed diagram keys → defaults/indexes/FK actions → text-domain index and workflow boundaries → freshness check in CI. The root targets `dev`; every following branch targets the preceding branch.

The reference covers **37 registered tables, 84 foreign-key constraints and 30 simple declared text domains** on 25 November. Composite foreign keys remain single tuple relations; cardinality uses model nullability and global uniqueness, excluding partial/expression indexes from global uniqueness inference. ERD key tokens derive from PostgreSQL types; exact types remain in the dictionary. Python defaults are labelled without invocation; no row values, credentials or database objects are queried.

Only complete simple text `IN` predicates enter the domain index. SQL-escaped quotes are decoded; numeric and compound predicates are not guessed into states. Their full CHECK expressions remain in the dictionary. Stored values do not define authorized workflow transitions: see [state boundaries](../data/state-boundaries.md).

From repository root, set `GISTAR_ENVIRONMENT=local` and run:

```bash
python api/scripts/export_schema_reference.py
python api/scripts/export_schema_reference.py --check
```

Generation writes the canonical reference for review. Checking is read-only, fails on missing/invalid/stale content and never overwrites evidence or creates output directories. CI runs `python scripts/export_schema_reference.py --check` from `api`, separately from the existing PostgreSQL migration/drift check. Model changes must regenerate the reference; contributor and agent instructions document that requirement.

Local evidence on 25 November: 31 offline exporter/schema/OpenAPI regressions passed, including a blocked engine connection and stale/invalid output checks. Ruff, TypeScript, 117 web tests, build and diff checks passed. Document links resolve and the canonical reference passes `--check`. No live PostgreSQL inspection, migration, application deployment, Mermaid image rendering or domain acceptance is claimed. CI completion was not awaited.

The dictionary describes registered metadata, not database triggers defined exclusively in migrations, API-only validators, deployed schema parity, execution of linked test suites or privacy approval. Those controls remain independent. No Jira transitions, automatic merges or deployments occurred.

## ES

KAN-216 está asignada a Elizabeth y tiene deadline **03/12/2026**. Implementación Yohanna; único revisor solicitado Anasfady. Se amplía el exportador existente, sin crear otra fuente de verdad ni modificar modelos operativos.

Orden: relaciones compuestas → claves tipadas → defaults/índices/acciones FK → dominios y límites de flujo → control CI. La raíz parte de `dev` y cada rama siguiente depende de la anterior.

La referencia recoge 37 tablas, 84 restricciones FK y 30 dominios textuales simples registrados. Conserva las relaciones compuestas; no interpreta índices parciales como unicidad global ni dominios como permisos. Muestra los defaults SQL declarados y marca los de Python sin ejecutarlos. Las restricciones compuestas permanecen completas, sin inventar estados.

Los comandos anteriores regeneran la referencia o comprueban su vigencia. `--check` no sobrescribe contenido obsoleto ni crea directorios. CI lo exige por separado de migraciones y pruebas de comportamiento; las instrucciones del equipo explican cuándo regenerar.

Evidencia local del 25/11: 31 regresiones offline, Ruff, TypeScript, 117 pruebas web, build y diff PASS. La referencia pasa `--check` y sus enlaces resuelven. No se consultó una base, ejecutaron migraciones, renderizó una imagen Mermaid ni desplegó la aplicación. No acredita triggers exclusivos de migraciones, validadores del API, ejecución de los tests enlazados, conformidad de privacidad o aceptación PO. No se esperó al CI ni se cambió Jira o fusionó ningún PR.
