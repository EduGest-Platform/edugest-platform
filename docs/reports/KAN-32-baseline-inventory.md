# Baseline inventory and recovery / Inventario base y recuperación — KAN-32

**Snapshot / Instantánea:** `dev` at `8481d0842f2784c51a40fcdde8bd2b5049e78c2e` · git tree `9f5732767194c8a28f41f54bea99b3f5610cfe5a` · 201 tracked files / archivos versionados · SHA-256 of `git ls-tree -r --name-only` output / de la salida de `git ls-tree -r --name-only`: `999300994a17fd63f9170e763764cab4689c8200157a4938b817953edb42f399`.
Historical references / referencias históricas: foundation `441772b5421a44d9f1733c6a738f4f844aba60b3` (PR #3); KAN-81 snapshot `dev@d60f61a`. Do not confuse the current `dev` with those snapshots / no confundir `dev` actual con esas instantáneas.

## ES — qué cubre
Cierra el criterio de KAN-32 «inventario exacto de frontend, API, migraciones y tests publicado en el repositorio». Complementa el mapa por responsabilidades de `docs/reports/KAN-95-97-repository-map.md` (que describe a `dev@8c3b869`, 156 archivos, y solo mencionaba la migración 0001). Es una lista de rutas versionadas: no contiene contenido, secretos ni datos personales, y la presencia de un archivo no prueba que se ejecute.

## EN — what it covers
Closes KAN-32's criterion "exact inventory of frontend, API, migrations and tests published in the repository". It complements the responsibility map in `docs/reports/KAN-95-97-repository-map.md` (which describes `dev@8c3b869`, 156 files, and listed only migration 0001). It lists tracked paths only: no content, secrets or personal data, and a file being present does not prove it runs.

## Counts / Recuento
| Category / Categoría | Files / Archivos |
|---|---|
| Frontend | 59 |
| API | 54 |
| Migrations | 2 |
| Tests | 30 |
| Infra, CI, docs and root config | 56 |
| **Total** | **201** |

Migrations on this snapshot / migraciones en esta instantánea: `0001` and `0003` (`0002` is reserved for F2 and absent on purpose; `0004`/`0005` live in open PRs / `0002` está reservada para F2 y ausente a propósito; `0004`/`0005` están en PR abiertas).

## Regenerate / Regenerar
```bash
git ls-tree -r --name-only 8481d0842f2784c51a40fcdde8bd2b5049e78c2e | wc -l
git rev-parse '8481d0842f2784c51a40fcdde8bd2b5049e78c2e^{tree}'
git ls-tree -r --name-only 8481d0842f2784c51a40fcdde8bd2b5049e78c2e | sha256sum
```

## Recovery procedure / Procedimiento de recuperación
1. **ES:** clonar limpio, nunca sobre un directorio con trabajo local: `git clone https://github.com/EduGest-Platform/edugest-platform.git && cd edugest-platform`. **EN:** clone into an empty directory, never over local work.
2. `git fetch origin && git checkout 8481d0842f2784c51a40fcdde8bd2b5049e78c2e` (or the snapshot commit to reproduce / o el commit de instantánea a reproducir).
3. **ES:** comparar `git rev-parse HEAD^{tree}` con `9f5732767194c8a28f41f54bea99b3f5610cfe5a`; si coincide, el contenido es idéntico. **EN:** compare the tree hash; a match means identical content.
4. **ES:** conservar intacto cualquier directorio anterior y sus cambios; todos los comandos de recuperación se ejecutan exclusivamente en el clon nuevo. Crear una rama no guarda por sí solo cambios sin commit ni archivos sin seguimiento. No cambiar de commit en el directorio anterior, ni usar `reset --hard` o `push --force`. **EN:** preserve every existing directory and its changes; run recovery commands exclusively in the new clone. Creating a branch alone does not save uncommitted or untracked work. Do not switch the old checkout, hard-reset or force-push.
5. **ES:** instalar y validar según `commands.md` (web: `pnpm install`; API: `api/` con PostgreSQL 16 y `alembic upgrade head`). **EN:** install and validate per `commands.md`.

## Evidence / Evidencia
- Generated with `git ls-tree` on a fresh fetch of `origin/dev`; no runtime tests (documentation-only) / generado con `git ls-tree` sobre `origin/dev`; sin pruebas de ejecución (solo documentación).
- Recovery steps are the standard git workflow and were not re-run in a clean clone for this change (KAN-82 validated an equivalent recovery earlier, per Yohanna's 17/11 comment) / los pasos son flujo git estándar y no se reejecutaron en un clon limpio para este cambio (KAN-82 validó una recuperación equivalente según el comentario de Yohanna del 17/11).

### Local re-verification / Reverificación local — 2026-11-19

**VERIFIED_RUNNING:** all 201 listed paths match this pinned commit exactly, without duplicates; path-list SHA-256 and tree SHA-1 match the header. A new local clone (`--no-hardlinks --no-checkout`, then detached checkout of the pinned SHA with `core.autocrlf=false`) recovered all 201 files; each file's bytes match its Git blob hash. Existing checkouts were untouched. This verifies source recovery, not dependency installation or application startup. / Las 201 rutas coinciden exactamente, sin duplicados; hashes de lista y árbol correctos. Un clon local nuevo recuperó los 201 archivos y cada contenido coincide con su objeto Git. No se tocaron directorios existentes. Se verifica recuperación de fuentes, no instalación ni arranque.

**NOT_RUN:** dependency installation, runtime/E2E and migrations in the recovery clone. PR #47 is already integrated; this follow-up verifies source recovery and corrects the preservation instructions. Yohanna reviews this additional evidence. / Instalación, ejecución/E2E y migraciones en ese clon no ejecutados. El PR #47 ya está integrado; este seguimiento verifica recuperación y corrige las instrucciones de conservación. Yohanna revisa esta evidencia adicional.

Run the following from the repository root of the new recovery clone, after checking out the pinned commit above. It only reads files and Git objects. / Ejecutar en la raíz del clon nuevo, situado en el commit fijado. Solo lee archivos y objetos Git:

```python
import hashlib
import subprocess
from pathlib import Path

baseline = "8481d0842f2784c51a40fcdde8bd2b5049e78c2e"
paths = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", baseline])
assert len(paths.splitlines()) == 201
assert hashlib.sha256(paths).hexdigest() == "999300994a17fd63f9170e763764cab4689c8200157a4938b817953edb42f399"
for entry in subprocess.check_output(["git", "ls-tree", "-r", baseline]).decode().splitlines():
    metadata, name = entry.split("\t", 1)
    mode, kind, expected = metadata.split()
    assert mode == "100644" and kind == "blob"
    data = Path(name).read_bytes()
    actual = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
    assert actual == expected, name
print("PASS: 201 recovered files and inventory hash match the pinned baseline")
```

## Inventory / Inventario

### Frontend (React/Vite/Tailwind, `.figma/`) — 59

- `.figma/README.md`
- `.figma/make/analyze-routes`
- `.figma/make/deploy`
- `.figma/make/deploy-preview`
- `.figma/make/dev`
- `.figma/make/dev.json`
- `.figma/make/format`
- `.figma/make/install`
- `.figma/make/langserver`
- `.figma/make/site.json`
- `index.html`
- `package.json`
- `pnpm-lock.yaml`
- `public/favicon.svg`
- `src/App.tsx`
- `src/gistar/Shell.tsx`
- `src/gistar/actions.ts`
- `src/gistar/analytics.ts`
- `src/gistar/components/AccessDenied.tsx`
- `src/gistar/components/AttendanceModal.tsx`
- `src/gistar/components/LoginScreen.tsx`
- `src/gistar/components/Modal.tsx`
- `src/gistar/components/ReviewModal.tsx`
- `src/gistar/components/ThisWeek.tsx`
- `src/gistar/components/charts.tsx`
- `src/gistar/config.ts`
- `src/gistar/contribution.md`
- `src/gistar/dates.ts`
- `src/gistar/domain.ts`
- `src/gistar/metrics.ts`
- `src/gistar/migrate.ts`
- `src/gistar/seed.json`
- `src/gistar/store.tsx`
- `src/gistar/types.ts`
- `src/gistar/ui.tsx`
- `src/gistar/views/Admin.tsx`
- `src/gistar/views/Applications.tsx`
- `src/gistar/views/Aspirant.tsx`
- `src/gistar/views/Assistant.tsx`
- `src/gistar/views/Calendar.tsx`
- `src/gistar/views/Catalog.tsx`
- `src/gistar/views/Dashboard.tsx`
- `src/gistar/views/Deliveries.tsx`
- `src/gistar/views/FollowUp.tsx`
- `src/gistar/views/GroupAnalytics.tsx`
- `src/gistar/views/Profile.tsx`
- `src/gistar/views/Rubrics.tsx`
- `src/gistar/views/Students.tsx`
- `src/gistar/views/api/ApiAdmissions.tsx`
- `src/index.css`
- `src/main.tsx`
- `src/shared/api/client.ts`
- `src/shared/api/config.ts`
- `src/shared/api/errors.ts`
- `src/shared/api/schema.gen.ts`
- `src/shared/api/session.tsx`
- `src/vite-env.d.ts`
- `tsconfig.json`
- `vite.config.ts`

### API (FastAPI) — 54

- `api/.env.example`
- `api/Dockerfile`
- `api/README.md`
- `api/alembic.ini`
- `api/alembic/env.py`
- `api/alembic/script.py.mako`
- `api/app/__init__.py`
- `api/app/core/__init__.py`
- `api/app/core/audit.py`
- `api/app/core/authz.py`
- `api/app/core/config.py`
- `api/app/core/db.py`
- `api/app/core/deps.py`
- `api/app/core/error_handling.py`
- `api/app/core/security.py`
- `api/app/core/text.py`
- `api/app/main.py`
- `api/app/models.py`
- `api/app/modules/__init__.py`
- `api/app/modules/admissions/__init__.py`
- `api/app/modules/admissions/models.py`
- `api/app/modules/admissions/router.py`
- `api/app/modules/admissions/schemas.py`
- `api/app/modules/admissions/service.py`
- `api/app/modules/audit/__init__.py`
- `api/app/modules/audit/models.py`
- `api/app/modules/audit/router.py`
- `api/app/modules/automation/__init__.py`
- `api/app/modules/automation/engine.py`
- `api/app/modules/catalog/__init__.py`
- `api/app/modules/catalog/models.py`
- `api/app/modules/catalog/router.py`
- `api/app/modules/catalog/schemas.py`
- `api/app/modules/identity/__init__.py`
- `api/app/modules/identity/models.py`
- `api/app/modules/identity/router.py`
- `api/app/modules/identity/schemas.py`
- `api/app/modules/integrations/__init__.py`
- `api/app/modules/integrations/github/README.md`
- `api/app/modules/integrations/github/__init__.py`
- `api/app/modules/integrations/github/client.py`
- `api/app/modules/integrations/github/config.py`
- `api/app/modules/integrations/github/schemas.py`
- `api/app/modules/integrations/github/service.py`
- `api/app/modules/integrations/github/urls.py`
- `api/app/modules/knowledge/__init__.py`
- `api/app/modules/knowledge/models.py`
- `api/app/modules/learning/__init__.py`
- `api/app/modules/learning/models.py`
- `api/app/seed.py`
- `api/docker-entrypoint.sh`
- `api/pyproject.toml`
- `api/scripts/__init__.py`
- `api/scripts/export_openapi.py`

### Migrations / Migraciones (Alembic) — 2

- `api/alembic/versions/0001_f1_cimientos.py`
- `api/alembic/versions/0003_rag_knowledge.py`

### Tests (API, web, evals) — 30

- `api/tests/__init__.py`
- `api/tests/conftest.py`
- `api/tests/test_api_errors.py`
- `api/tests/test_applications.py`
- `api/tests/test_auth.py`
- `api/tests/test_contract.py`
- `api/tests/test_crm_audit.py`
- `api/tests/test_github_integration.py`
- `api/tests/test_knowledge_models.py`
- `api/tests/test_rbac.py`
- `api/tests/test_rbac_regression.py`
- `api/tests/test_registration_validation.py`
- `evals/automation/README.md`
- `evals/automation/metrics.py`
- `evals/automation/test_dst_deadlines.py`
- `evals/automation/test_offline.py`
- `evals/rag/corpus/A1-brief-recetario.md`
- `evals/rag/corpus/A2-calendario-v2.md`
- `evals/rag/corpus/A3-calendario-v1.md`
- `evals/rag/corpus/A4-normas-asistencia.md`
- `evals/rag/corpus/A5-criterios-evaluacion.md`
- `evals/rag/corpus/B1-brief-detector-plagas.md`
- `evals/rag/corpus/corpus.json`
- `evals/rag/questions.jsonl`
- `evals/rag/smoke_adr0005.py`
- `evals/rag/validate_bank.py`
- `src/gistar/__tests__/flows.test.ts`
- `src/gistar/__tests__/migrate.test.ts`
- `src/shared/api/__tests__/errors.test.ts`
- `src/shared/api/__tests__/session-end.test.ts`

### Infra, CI, docs and root config / Infra, CI, docs y configuración raíz — 56

- `.dockerignore`
- `.gitattributes`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `.github/workflows/ci.yml`
- `.github/workflows/e2e-f1.yml`
- `.gitignore`
- `.mise.toml`
- `AGENTS.md`
- `AUDITORIA_CODEX_ESTADO_ACTUAL.md`
- `CLAUDE.md`
- `CONSTITUTION.es.md`
- `CONSTITUTION.md`
- `Dockerfile`
- `README.md`
- `commands.md`
- `contracts/openapi.json`
- `contribution.md`
- `docs/00-diagnostico.md`
- `docs/01-gap-to-be.md`
- `docs/02-arquitectura-y-contratos.md`
- `docs/03-plan-equipo-pruebas-riesgos.md`
- `docs/README.md`
- `docs/adr/0001-web-en-la-raiz.md`
- `docs/adr/0002-fastapi-monolito-modular-postgresql.md`
- `docs/adr/0003-sesiones-opacas-y-rbac-por-ambito.md`
- `docs/adr/0004-conmutador-local-api.md`
- `docs/adr/0005-stack-ia-asistente-en.md`
- `docs/adr/0005-stack-ia-asistente-es.md`
- `docs/adr/0008-despliegue-y-ci-cd.md`
- `docs/deploy/KAN-142-render-feasibility.md`
- `docs/deploy/README.md`
- `docs/incrementos/F1-cimientos.md`
- `docs/producto/diccionario-campos-candidatura.md`
- `docs/reports/CONSTITUTION_IMPLEMENTATION_REPORT.md`
- `docs/reports/F1_GIT_DOCKER_POSTGRES_FASTAPI_REPORT.md`
- `docs/reports/KAN-109-f1-rbac-regression.md`
- `docs/reports/KAN-114-dropout-definition.es.md`
- `docs/reports/KAN-114-dropout-definition.md`
- `docs/reports/KAN-120-crm-event-policy.md`
- `docs/reports/KAN-121-160-task-rule-catalogue.md`
- `docs/reports/KAN-124-registration-validation.md`
- `docs/reports/KAN-209-logs-export-retention.md`
- `docs/reports/KAN-95-97-repository-map.md`
- `e2e/F1-registration.md`
- `e2e/cdp.mjs`
- `e2e/f1-api-mode.mjs`
- `e2e/f1-registration.mjs`
- `e2e/local-mode.mjs`
- `infra/.env.example`
- `infra/compose.yaml`
- `infra/initdb/01-test-db.sql`
- `infra/mlflow.Dockerfile`
- `infra/nginx.conf`
- `infra/smoke-test.sh`
- `projectplan.md`
- `render.yaml`
