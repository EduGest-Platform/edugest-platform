# KAN-153 / KAN-128 — recovered regression evidence / Regresiones recuperadas

Date / Fecha: 19 November 2026. Base: `dev@c59d201ddcb92ad6043bb3fad056e8a324deaea7`.
Owner: Elizabeth. Reviewer: Yohanna (rollback); David (requirement-review CORS).

**ES:** KAN-153 y KAN-128 ya están integrados (#46/#40). Este seguimiento recupera pruebas locales que aún faltaban en `dev`; no reaplica correcciones absorbidas ni cambia comportamiento, permisos, contrato o migraciones.

**EN:** KAN-153 and KAN-128 are already integrated (#46/#40). This follow-up recovers missing local regressions without reapplying absorbed fixes or changing runtime behaviour, permissions, contracts or migrations.

- `test_audit_failure_rolls_back_stage_decision_and_crm`: falla la auditoría durante una decisión y comprueba desde otra sesión PostgreSQL que etapa, decisión y eventos CRM no cambian. / Fails auditing during a decision and verifies persisted rollback from an independent database session.
- `test_cors_preflight.py`: acepta PUT con origen configurado y cabeceras de autenticación; rechaza origen ajeno. / Accepts authenticated PUT preflight from a configured origin and rejects an unknown origin.

## Actual checks / Comprobaciones reales — VERIFIED_RUNNING

Only a new disposable PostgreSQL 16 + pgvector, synthetic fixtures, loopback port 55434 was used. Existing project services were untouched. / Solo PostgreSQL nuevo desechable, fixtures sintéticos, puerto local 55434; servicios existentes intactos.

| Command (from `api/` unless stated) / Comando | Result / Resultado |
|---|---|
| `python -m pytest -q -o addopts='' --tb=short` | PASS: 558 tests, including the independent-session rollback; 550.61 s |
| `python -m pytest --noconftest tests/test_cors_preflight.py -o addopts='' -q` | PASS: 2 tests; added after the full suite collected its files, therefore run separately |
| `python -m alembic heads` / `current` | PASS: single head `0005`, database at head |
| `python -m alembic check` | PASS: no new upgrade operations detected |
| `ruff check api --select E4,E7,E9,F` (Ruff 0.17.5, repo root) | PASS |
| `pnpm exec tsc --noEmit -p .` / `pnpm test` / `pnpm build` (repo root) | PASS / PASS: 48 / PASS |
| `pnpm gen:api` and `git diff --exit-code -- src/shared/api/schema.gen.ts` | PASS: generated client unchanged |
| `git diff --check` | PASS |

**ES:** para reproducir, configurar `GISTAR_ENVIRONMENT=local` y `GISTAR_TEST_DATABASE_URL` exclusivamente a una BD nueva desechable. El conftest borra/recrea esquema y datos; nunca apuntarlo a una BD existente. La suite final conjunta contiene 560 pruebas; los resultados anteriores son dos ejecuciones, no un único rerun completo. El flujo de navegador y CI del nuevo PR aún no se habían ejecutado al preparar este informe; consultar sus checks para evidencia posterior. No se despliega ni se fusiona.

**EN:** reproduce with local configuration and a newly created disposable test URL only. Conftest resets schema/data; never use an existing database. Final coverage is 560 tests across the two commands above, not one complete rerun. Browser E2E and this new PR's CI had not run when this report was prepared; later checks are separate evidence. No deployment or merge.
