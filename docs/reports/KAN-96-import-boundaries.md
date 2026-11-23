# KAN-96 — Web import boundaries / Límites de importación de la web

Inspected / Inspeccionado: 2026-11-19, `dev` at `6a55b66` (274 tracked files), compared with PR #3 foundation `441772b5` (139 files). Owner: Yohanna. Cross-review: **Anas** (frontend): this PR is the review request. Complements [KAN-95/97 repository map](KAN-95-97-repository-map.md). No folders moved, no aliases changed, Figma Make scaffold and canonical instructions untouched. No secrets.

## EN

### Tree compared with PR #3

| Folder | `441772b5` | `dev` | Change |
|---|---|---|---|
| `src/` (entry: `main.tsx`, `App.tsx`, `index.css`, `vite-env.d.ts`) | 4 | 4 | same |
| `src/gistar/` (domain, store, seed, config) | 13 | 14 | `requirements.ts` added |
| `src/gistar/components/` | 6 | 8 | `AccessDenied`, `RequirementReviewPanel` added |
| `src/gistar/views/` + `views/api/` | 13 + 1 | 13 + 1 | same |
| `src/gistar/demo/` | — | 1 | requirement examples for local demo |
| `src/shared/api/` (+ `__tests__/`) | 4 | 5 + 2 | `errors.ts` and tests added |

The structure from PR #3 still holds. Growth stayed inside the existing folders, with no new top-level packages.

### Boundaries found, now enforced by `src/shared/__tests__/import-boundaries.test.ts`

1. **Nothing in `src/` imports from outside `src/`** (`api/`, `ml/`, `e2e/`, `infra/`). The web reaches the backend only over HTTP through the generated contract (`contracts/openapi.json` → `schema.gen.ts`).
2. **Runtime packages are only** `react`, `react-dom`, `lucide-react` and `openapi-fetch`. Tests may also use `vitest`. Imports of `node:*` and `react-dom/server` are limited to files under `__tests__/`. A new package needs a PR that updates this list on purpose.
3. **Only `gistar/views/api/` (and `shared/api/` itself) import the HTTP client.** Local views never make HTTP calls, which keeps local and API data apart (ADR-0004).
4. **`shared/` does not depend on `gistar/`** except for type-only imports. Today there is exactly one: `shared/api/session.tsx` imports the `Role` type.

The test checks the source text, not the compiled bundle. Mutation check: three probe files, one breaking each of rules 1, 3 and 4, made the matching tests fail. After removing them, 53/53 pass.

**Import forms checked (review follow-up):** static `import … from` / `export … from`, side-effect `import 'x'` and dynamic `import('x')` with a literal path. Rules 1, 3 and 4 apply to relative paths **and** to the `@/` alias, resolved to `src/` like `tsconfig.json` and Vite. Six regression tests cover the alias, literal dynamic imports, side-effect imports and type-only imports of the client (allowed: they make no HTTP call). Rule 3 ignores type-only imports. Not checked: `require()`, dynamic imports with a computed path, and the checker file itself (its fixtures are strings). Vitest local 59/59, `tsc` PASS.

### Findings and decisions (for Anas to confirm)

- The `@/` alias is declared in `tsconfig.json` and `vite.config.ts` but **no file uses it**; all imports are relative. Decision proposed: keep the alias (Make scaffold), do not mass-rewrite imports; new code may use either.
- `ApiAdmissions.tsx` imports `../../../shared/api/...` (three levels). This is acceptable now. If more API views arrive, consider `@/shared/api/...`. Not done here to avoid a broad refactor.
- No `src/components/ui/` exists. The shared UI kit is `src/gistar/ui.tsx`.
- **Public documentation decision:** this report and the boundary test are safe to publish. They contain tracked paths and rules only, with no environment values, personal data or credentials.

### Evidence

| Check (Windows 10, Node 24.18.0, pnpm 10.34.3) | Result |
|---|---|
| `pnpm test` | PASS: 6 files, 53 tests (48 existing + 5 boundary tests) |
| Mutation probes (rules 1, 3, 4) | 3 expected failures, then PASS after removal |
| `pnpm exec tsc --noEmit -p .` | PASS |
| `git ls-tree` comparison `441772b5` vs `dev` | Table above |

## ES

**Árbol.** La estructura del PR #3 se mantiene: el crecimiento (requisitos, `AccessDenied`, `RequirementReviewPanel`, `errors.ts`, demo de requisitos) cabe en las carpetas existentes.

**Límites, ahora comprobados por una prueba Vitest:**
1. Nada de `src/` importa de fuera de `src/`; la web llega al backend solo por HTTP y contrato generado.
2. Paquetes de ejecución permitidos: `react`, `react-dom`, `lucide-react` y `openapi-fetch`. Los imports de `node:*` y `react-dom/server` se limitan a archivos bajo `__tests__/`.
3. Solo `gistar/views/api/` (y la propia `shared/api/`) usan el cliente HTTP; las vistas locales nunca llaman a la API.
4. `shared/` no depende de `gistar/` salvo importaciones de solo tipos (hoy una: `Role`).

**Formas comprobadas (tras la revisión):** `import … from`, `export … from`, `import 'x'` e `import('x')` con ruta literal. Las reglas 1, 3 y 4 se aplican a rutas relativas y al alias `@/` (resuelto a `src/`). Seis pruebas de regresión cubren alias, imports dinámicos, de efecto lateral y de solo tipos (la regla 3 ignora los de solo tipos: no hacen llamadas HTTP). No se comprueban `require()`, imports dinámicos con ruta calculada ni el propio archivo de la prueba.

**Hallazgos para que Anas confirme.** El alias `@/` existe pero no se usa: se conserva, sin reescritura masiva. Las importaciones de tres niveles en `ApiAdmissions.tsx` son aceptables por ahora. No hay `src/components/ui/`; el kit de interfaz es `src/gistar/ui.tsx`. El informe y la prueba pueden publicarse: solo contienen rutas y reglas, sin secretos ni datos personales.

**Evidencia.** Vitest 59/59 (tras la revisión; antes 53/53), sondas de mutación fallan como se espera, `tsc` PASS.
