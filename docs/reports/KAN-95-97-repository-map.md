# Repository map / Mapa del repositorio — KAN-95, KAN-97

**Inspected / Inspeccionado:** 2026-11-17, `dev` at `8c3b869692eff4a5116f7514fd258d41d8b256bd` (156 tracked files / archivos versionados).
Foundation reference / referencia inicial: `441772b5421a44d9f1733c6a738f4f844aba60b3` (PR #3).
Owner / responsable: Yohanna. Reviewer / revisión: Elizabeth; Anas for import boundaries / para límites de importación (KAN-96, review still pending / pendiente).

## ES — alcance y estructura comprobada

Mapa estático del árbol Git y de las configuraciones, **CODE_PRESENT_NOT_RUN** para los componentes descritos. No certifica arranque, seguridad ni ausencia de secretos. Los comandos de inspección y validación documental se ejecutaron; no se han movido carpetas, cambiado alias ni modificado instrucciones canónicas.

| Ruta | Función y responsable de integración |
|---|---|
| `src/main.tsx`, `src/App.tsx`, `src/index.css` | Entradas React y Tailwind 4; frontend de Anas. |
| `src/gistar/` | Vistas, componentes, dominio y seed de demo local; datos locales no equivalen a API persistida. |
| `src/shared/api/` | Cliente HTTP, sesión y conmutador de vistas; `schema.gen.ts` se genera desde OpenAPI. |
| `api/app/core/` | Configuración, DB, sesiones, autorización y auditoría; Elizabeth. Cambios de permisos requieren revisión cruzada. |
| `api/app/modules/` | En esta base: admissions, audit, automation, catalog, identity, learning. `learning` solo tiene Enrollment; no implica F3 terminado. `automation` es el motor offline de reglas (PR #10). |
| `api/app/seed.py` | Carga sintética del servidor; Elizabeth. La entrada semilla compartida es `src/gistar/seed.json`. |
| `api/alembic/versions/` | Solo `0001_f1_cimientos.py` en este commit. No reservar nuevos números sin coordinar con Elizabeth/David. |
| `contracts/openapi.json` | Contrato generado; se actualiza con el cambio de API, sin resolver divergencias a mano. |
| `api/tests/`, `src/gistar/__tests__/`, `evals/automation/` | Pruebas API/PostgreSQL, Vitest y evaluador offline de automatización (`unittest`); presencia no certifica ejecución. |
| `e2e/` | Scripts actuales CDP (`cdp.mjs`, `f1-api-mode.mjs`, `local-mode.mjs`); no es una suite Playwright ya integrada. Yohanna. |
| `infra/`, Dockerfiles, `render.yaml` | Compose, PostgreSQL/initdb, web nginx, MLflow y preparación Render; Yohanna. Publicar requiere aprobación. |
| `.github/workflows/ci.yml` | Jobs automation, web, API, secrets y compose en esta base; revisar Checks por commit. Yohanna. |
| `.figma/`, `vite.config.ts`, `.mise.toml` | Compatibilidad de Make y herramientas; conservar estructura y plugins existentes. |
| `docs/` | Diagnóstico, arquitectura, decisiones, despliegue e informes con estados de evidencia. |

En el commit inspeccionado no hay `ml/` ni módulos `knowledge`, `agents`, `risk` o `integrations`. `evals/` solo contiene `automation/` (PR #10, ya fusionado). Pueden existir propuestas en otras ramas: no duplicarlas ni describirlas como integradas en `dev`. El PR #7 contiene trabajo independiente de este mapa y necesita su propia revisión.

## EN — verified layout and boundaries

This is a static Git/configuration map, **CODE_PRESENT_NOT_RUN** for the listed components, not a runtime/security/secret-free certification. Inspection and documentation checks were executed. No folders, aliases or canonical instructions were changed.

React/Tailwind starts at `src/main.tsx`, `src/App.tsx` and `src/index.css`; Anas owns frontend integration. `src/gistar/` contains the local demo/domain/seed, while `src/shared/api/` contains HTTP/session/view switching and the generated client. Local data is not persisted API data.

Elizabeth owns `api/app/core/`, backend modules and server seed. Current modules are admissions, audit, automation, catalog, identity and learning; learning only contains Enrollment, not completed F3. Only migration 0001 exists at this snapshot. Coordinate future migration numbers with Elizabeth/David. Regenerate OpenAPI and its TypeScript client together.

Yohanna owns infrastructure, E2E and CI integration. Current E2E scripts use CDP, not an already integrated Playwright suite. CI defines automation/web/API/secrets/compose jobs; inspect actual Checks per commit. Render files prepare deployment, which still needs explicit approval.

No `ml/` or knowledge/agents/risk/integrations modules exist in this inspected commit, and `evals/` only holds `automation/` (PR #10, merged); other branches may propose more. Do not duplicate PR #7 or describe its contents as merged. Documentation and code presence alone do not establish working features.

## Import/configuration guardrails / Límites de configuración

- **ES:** `tsconfig.json` resuelve `@/*` a `./src/*`; Vite define `@` con `path.resolve(__dirname, './src')`. No introducir otro alias ni mover la web a `apps/` sin ADR. **EN:** keep matching TypeScript/Vite aliases and the root frontend layout; changes require a justified ADR.
- **ES:** conservar plugins de React, Tailwind y Make, y las importaciones CSS; no migrar framework ni crear una segunda configuración Tailwind. **EN:** preserve React/Tailwind/Make plugins and CSS imports; no framework migration or parallel Tailwind setup.
- **ES:** API usa `app.*` desde `api/`; web llega por HTTP/contrato, no importa modelos Python. Regenerar `contracts/openapi.json` y `src/shared/api/schema.gen.ts` juntos. **EN:** keep API imports rooted in `api/`; frontend uses HTTP/generated contracts rather than Python internals.
- **ES:** jerarquía coherente: CONSTITUTION → AGENTS → CLAUDE; reparto confirmado y datos sintéticos. Ningún documento autoriza por sí solo commits, PR, Jira o despliegue. **EN:** canonical hierarchy and team roles agree; synthetic data only, explicit authorization for external changes.
- **ES:** no publicar `.env`, tokens, datos reales ni archivos privados. Este mapa publica rutas versionadas y responsabilidades, no contenidos sensibles ni un escaneo de secretos. **EN:** publish tracked paths/responsibilities only; do not include secrets, personal data or private files. This is not a secrets scan.

## Evidence / Evidencia

- `git ls-tree -r --name-only <commit>`: 156 tracked paths; checked listed modules, migration and entry points / 156 rutas, comprobados módulos, migración y entradas.
- Read / lectura: `vite.config.ts`, `tsconfig.json`, `package.json`, `AGENTS.md`, `CLAUDE.md`, `CONSTITUTION.md` and API/test entry points.
- Local Markdown links and path/configuration checks: PASS / enlaces locales y comprobaciones de rutas/configuración correctos (commands recorded in PR / comandos resumidos en PR).
- No runtime tests for this documentation-only change / sin pruebas de ejecución para este cambio documental.

KAN-95/KAN-97 need Elizabeth's cross-review before closure. Import-boundary review with Anas (KAN-96) has **not** occurred merely by creating this document. / Se requiere revisión de Elizabeth para cerrar; la revisión con Anas no se da por realizada.
