# KAN-124 — Trim before text validation / Normalizar antes de validar

Date / Fecha: 2026-11-18. Base: `dev` at `8481d0842f2784c51a40fcdde8bd2b5049e78c2e`.
Branch: `fix/KAN-124-trim-before-validation`.

**VERIFIED_RUNNING:** direct schema tests and the complete local PostgreSQL-backed API suite. KAN-124 is not complete; cross-review and acceptance remain pending.

**ES:** Esquemas y suite API completa probados localmente con PostgreSQL. No se declara KAN-124 finalizada ni se modifica su asignación; faltan revisión cruzada y aceptación.

## Problem and change / Problema y cambio

`ApplicationCreate` validated the length of `nombre` and `motivacion` before stripping whitespace. Whitespace could satisfy a minimum and subsequently become empty; padded valid text could exceed the maximum before normalization. `EventCreate.resumen` had no trimming. These defects were recorded as three strict expected failures in the merged PR #22.

The validators now trim strings before existing Pydantic length constraints. A shared helper leaves other input types untouched for normal Pydantic handling. Internal whitespace remains intact. Numeric/null invalid inputs still produce structured validation errors. Field bounds, email handling, availability, required fields, JSON schemas, permissions, persistence and migration history are unchanged.

**ES:** Se quitan espacios exteriores antes de comprobar longitudes en nombre, motivación y resumen CRM. Se conservan espacios interiores y la validación habitual de tipos. Se mantienen los límites y campos existentes, sin cambiar requisitos funcionales de admisión, permisos ni BD.

## Files / Archivos

- [schemas.py](../../api/app/modules/admissions/schemas.py): string-only normalization before length validation.
- [test_admissions_text.py](../../api/tests/test_admissions_text.py): 38 direct schema cases for ASCII/Unicode whitespace, padded minimum/maximum boundaries, excessive lengths, invalid types and internal whitespace.
- [test_registration_validation.py](../../api/tests/test_registration_validation.py): remove the three strict expected failures; assert 422, field location and unchanged record counts/call counters on rejection. All three cases passed against local PostgreSQL.

**ES:** Normalización backend, 38 casos de esquema y conversión de los tres fallos esperados en pruebas normales, con comprobaciones de ausencia de mutaciones verificadas en BD local.

## Evidence / Evidencias

Executed on local Windows with the existing project virtual environment `api/.venv`: pytest 9.2.0, Pydantic 2.14.3. With explicit PO authorization, installed the already-declared pgvector dependency (resolved version 0.5.1) in that environment. Import verification and `pip check` passed. Synthetic inputs only.

From `api/`, using that environment's Python executable:

```powershell
& $python -m pytest --noconftest tests/test_admissions_text.py -o addopts= -q
```

`--noconftest` deliberately excludes the database/autouse fixtures for this direct-schema test file; it does not certify the API, PostgreSQL persistence or RBAC. The same file is discovered normally by the full API suite when its environment is ready.

The full suite was subsequently run normally, without `--noconftest`, using the isolated worktree's API source and the existing project Python executable:

```powershell
# GISTAR_TEST_DATABASE_URL was set only for the test process to the disposable local DB.
& $python -m pytest -o addopts= -q --tb=short
```

The test server was a fresh `pgvector/pgvector:pg16` container named `codex-kan124-pg-20261118`, bound only to `127.0.0.1:55432`, database `kan124_test`. Source path and database target were verified before execution. Fixtures ran migrations and synthetic reseeding there. The container was stopped and automatically removed after the run; normal local services and the working database were untouched.

| Check / Comprobación | Status | Actual result / Resultado real |
|---|---|---|
| Before schema fix, same 38 cases | FAIL | 16 failed, 22 passed |
| After schema fix | PASS | 38 passed |
| Input JSON schema comparison | PASS | SHA-256 before/after identical: `17bd820cff4e87ce035041289d978d583884067c4e233be181b5483f228609fa` |
| Full local API suite | PASS | 198 passed, 0 failed, 0 skipped, in 133.30 seconds; normal fixtures and PostgreSQL 16 + pgvector |
| Three formerly expected failures and API/RBAC regression | PASS | All three cases passed normally; regression tests included in the 198-test suite |
| Full exported OpenAPI equality and bearer declaration | PASS | Both contract tests passed in the complete API suite |
| Environment dependency integrity | PASS | pgvector 0.5.1 import and `pip check` |
| Web/typecheck/build/E2E | NOT_RUN | Backend input-normalization scope; no UI or generated contract changes |
| CI for this delivery | NOT_RUN | Unpublished local change |

**ES:** Se reprodujo el defecto antes del arreglo y se obtuvo 38/38 después. Tras instalar pgvector en el entorno virtual autorizado, la suite completa pasó 198/198, incluidos los tres antiguos xfail, regresión de permisos y dos pruebas de contrato. Se usó y retiró un contenedor PostgreSQL local desechable; los fixtures solo recrearon y sembraron esa BD de pruebas.

## Remaining gate / Validación pendiente

Local API regression is verified. Obtain cross-review and PO acceptance; inspect CI for the eventual published head rather than reusing this local result as CI evidence. Existing fixtures downgrade the test schema and reseed synthetic records; any repeat run must use a verified disposable database, never the working/demo database.

**ES:** Regresión API local verificada. Faltan revisión cruzada, aceptación y CI del eventual head publicado. Los fixtures destruyen/recrean el esquema de pruebas: cualquier repetición debe usar otra BD desechable, nunca la de trabajo ni una compartida.
