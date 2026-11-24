# KAN-215 — Implementation / Implementación

## ES

Implementación: Yohanna. Tarea asignada a Elizabeth; único revisor solicitado: Anasfady. Deadline Jira: **03/12/2026**. Incremento del 24/11/2026.

Actualiza los enlaces de instalación de README y API y aporta una guía bilingüe completa para PowerShell/POSIX. Incluye secretos locales, compose con env-file explícito, migraciones, seed idempotente, contrato y base de pruebas aislada. Corrige uvicorn para localhost y no-access-log, evitando duplicar URLs sin sanear.

## EN

Implementation: Yohanna. Jira assignee: Elizabeth. Sole requested reviewer: Anasfady.

Adds a complete bilingual PowerShell/POSIX installation and migration runbook, linked from both READMEs. Explains explicit compose env files, non-overwriting secret setup, migration working directory, seed idempotency, contract generation and destructive test-DB isolation; fixes the uvicorn example to bind localhost and disable raw access logs.

## Validation / Validación

PASS: all local Markdown links resolve and diff checks pass. Commands checked against package.json, .mise.toml, Alembic configuration, Docker entrypoint and test conftest. This documentation revision does not claim a fresh installation or PostgreSQL execution.

## Limits / Límites

Documentation only, based on #135. It does not execute migrations, seed resets, deployment or tests against a database. Existing local secrets are not modified. / Solo documentación; instalación completa no ejecutada.

CI completion is not awaited, as requested. No Jira changes, merge or deployment. / No se espera al CI por petición del usuario. No se cambia Jira ni se fusiona o despliega.
