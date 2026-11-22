# KAN-88 — Vitest configured and running / Vitest configurado y en ejecución

Base: `dev` at `6a55b66`. Machine: Windows 10 Pro, Node 24.18.0, pnpm 10.34.3, Vitest 5.1.0, clean worktree with `pnpm install --frozen-lockfile`. No business logic changed. This PR adds only this report. Synthetic data only.

## EN

**How Vitest is configured on `dev`.**
- `pnpm test` = `vitest run`, the same command CI runs in the `web` job (Ubuntu, Node 22) together with `tsc`, `build` and the generated-client check.
- There is no separate Vitest config today. Vitest reads `vite.config.ts` (the Figma Make config), so tests load the Make plugins they do not need. They also hit the Windows `EPERM` when `node_modules/.vite-temp` is not writable.
- That is fixed in the KAN-87 PR: a dedicated `vitest.config.ts` plus `--configLoader runner`, with `vite.config.ts` untouched. This report shows the current state of `dev` before that fix.

**Run result (`pnpm test`, 2026-11-19):** PASS, 5 files, 48 tests, 3.0 s.

| File | Tests | What it protects |
|---|---|---|
| `src/gistar/__tests__/flows.test.ts` | 10 | Local demo flows: cohort analytics, competency catalogue, rubric publishing, coder visibility, attendance and alerts, filters, role access |
| `src/gistar/__tests__/migrate.test.ts` | 6 | `localStorage` data migration v1 → v2 |
| `src/gistar/__tests__/requirements.test.ts` | 8 | Requirement review summary: never "rejected", exceptions, human decision |
| `src/shared/api/__tests__/errors.test.ts` | 18 | API error mapping (401/403/404/422, messages without personal data) |
| `src/shared/api/__tests__/session-end.test.ts` | 6 | Session end on 401, once only, late 401 from an old session ignored |

| Other checks | Result |
|---|---|
| `pnpm exec tsc --noEmit -p .` | PASS |
| `pnpm build` | PASS (`dist/assets/index-*.js` 443 kB, gzip 126 kB) |
| `node_modules/.vite-temp` write-denied (KAN-87 reproduction) | FAIL with `EPERM` on `dev`; PASS with the KAN-87 branch |

**Useful commands.**

```bash
pnpm test                                    # all unit tests, once
pnpm exec vitest run src/shared/api          # one folder
pnpm exec vitest                             # watch mode while developing
```

NOT_RUN: coverage report (no coverage tool is installed; adding one is a dependency decision for Anas). Browser E2E is a separate suite (`e2e/`) and was not run.

## ES

**Configuración en `dev`.** `pnpm test` ejecuta `vitest run`, igual que el job `web` del CI. No hay configuración propia de Vitest: lee `vite.config.ts` de Figma Make, de ahí el `EPERM` en Windows cuando `node_modules/.vite-temp` no admite escritura. Lo corrige el PR de KAN-87 sin tocar `vite.config.ts`.

**Resultado (19/11/2026, Windows):** 5 archivos, 48 pruebas PASS en 3,0 s. `tsc` y `build` PASS. Tabla de cobertura funcional arriba.

**No ejecutado:** informe de cobertura (no hay herramienta instalada; añadirla es decisión de dependencias de Anas) ni E2E de navegador.
