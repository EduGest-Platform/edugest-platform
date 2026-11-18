# KAN-91 — Contract verification / Verificación de contratos

Status / Estado: VERIFIED locally on `dev` 8481d08 (synthetic data, no deployment). NOT_RUN: frontend consuming the client, e2e. / Verificado en local sobre `dev` 8481d08. No ejecutado: consumo desde el frontend, e2e.

## ES · Qué se comprobó

| Comprobación | Resultado |
|---|---|
| `contracts/openapi.json` frente a la API: `scripts/export_openapi.py` regenera el contrato y se compara byte a byte | Idéntico (`tests/test_contract.py`, 2 passed) |
| `src/shared/api/schema.gen.ts` frente al contrato: se regenera con `openapi-typescript` 7.13.0 (la versión fijada en `pnpm-lock.yaml`) | Idéntico |
| Todas las operaciones privadas declaran autenticación Bearer | Cumple; las públicas son solo `POST /applications`, `GET /calls`, `POST /auth/login` y `GET /health` |
| Tamaño del contrato | 12 operaciones, OpenAPI 3.1.0 |

En el CI estas dos comprobaciones corren solas: el job `api` ejecuta `test_contract.py` y el job `web` ejecuta `pnpm gen:api && git diff --exit-code src/shared/api/schema.gen.ts`. Los dos aparecen en verde en los PR #37 a #39, que parten de `dev`.

Versiones usadas en local: fastapi 0.165.0, pydantic 2.14.3, starlette 1.10.0, sqlalchemy 2.1.9, alembic 1.20.1 (Python 3.12).

Para repetirlo: `cd api && python scripts/export_openapi.py` y `pnpm gen:api`; si `git diff` no muestra cambios, el contrato y el cliente están sincronizados.

**Hallazgo (PROPOSED, no aplicado):** `api/pyproject.toml` declara las dependencias con `>=` y no hay archivo de bloqueo. Una versión nueva de FastAPI o Pydantic puede cambiar el contrato generado y romper el CI sin que cambie el código. Opciones: un archivo de restricciones con versiones fijas o un lock. Requiere decisión del equipo.

## EN · What was checked

| Check | Result |
|---|---|
| `contracts/openapi.json` against the API: `scripts/export_openapi.py` regenerates the contract and it is compared byte for byte | Identical (`tests/test_contract.py`, 2 passed) |
| `src/shared/api/schema.gen.ts` against the contract: regenerated with `openapi-typescript` 7.13.0 (the version pinned in `pnpm-lock.yaml`) | Identical |
| Every private operation declares Bearer authentication | Met; the public ones are only `POST /applications`, `GET /calls`, `POST /auth/login` and `GET /health` |
| Contract size | 12 operations, OpenAPI 3.1.0 |

CI runs both checks on its own: the `api` job runs `test_contract.py` and the `web` job runs `pnpm gen:api && git diff --exit-code src/shared/api/schema.gen.ts`. Both are green on PRs #37 to #39, which branch from `dev`.

Local versions: fastapi 0.165.0, pydantic 2.14.3, starlette 1.10.0, sqlalchemy 2.1.9, alembic 1.20.1 (Python 3.12).

To repeat it: `cd api && python scripts/export_openapi.py` and `pnpm gen:api`; if `git diff` shows nothing, contract and client are in sync.

**Finding (PROPOSED, not applied):** `api/pyproject.toml` declares dependencies with `>=` and there is no lock file. A new FastAPI or Pydantic release can change the generated contract and break CI without any code change. Options: a constraints file with pinned versions, or a lock. The team has to decide.
