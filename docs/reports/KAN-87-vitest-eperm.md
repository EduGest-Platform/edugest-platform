# KAN-87 — Vitest EPERM: reproduction and fix / reproducción y corrección

Base: `dev` at `6a55b66`. Machine: Windows 10 Pro, Node 24.18.0, pnpm 10.34.3, Vitest 5.1.0. No business logic changed. No secrets or personal data involved.

## EN

**Root cause.** Before running any test, Vite bundles `vite.config.ts` into a temporary file `node_modules/.vite-temp/vite.config.ts.timestamp-*.mjs`. When that folder can't be written (locked by antivirus or an indexer, a sandbox, or wrong ACLs), Vitest stops with `EPERM: operation not permitted, open '...node_modules\.vite-temp\...'`. This matches the failure in `AUDITORIA_CODEX_ESTADO_ACTUAL.md` (R-05, AUD-005). The earlier note that the error was "transient" was right about its intermittency, but it never found the cause.

**Reproduction (deterministic, safe).** The test runs in a disposable worktree. It changes only the ACL of the worktree's own `node_modules/.vite-temp` and restores it afterwards:

```bash
mkdir -p node_modules/.vite-temp
icacls "node_modules\.vite-temp" /deny "%USERNAME%:(OI)(CI)(W,WD,AD)"
pnpm exec vitest run          # before: Startup Error, EPERM ... .vite-temp\vite.config.ts.timestamp-...mjs
icacls "node_modules\.vite-temp" /remove:d "%USERNAME%"
```

**Fix.**
- Add a dedicated `vitest.config.ts`. It sets only the `@` alias and the test glob, with no `__dirname` and no JSON import.
- `pnpm test` now runs `vitest run --configLoader runner`. The runner loader evaluates the config in memory and writes nothing to `.vite-temp`.
- `vite.config.ts` (Figma Make) is untouched. `vitest.config.ts` is added to `tsconfig.json` so it gets type-checked.

**Why not the other loaders.** With the current `vite.config.ts`, `--configLoader runner` fails (`__dirname is not defined`) and `native` fails (the JSON import needs an import attribute). Changing the Make config was out of scope, hence the separate file.

| Check (Windows, this branch) | Result |
|---|---|
| `pnpm test` with `.vite-temp` write-denied (before fix, `dev`) | FAIL: `EPERM` |
| `pnpm test` with `.vite-temp` write-denied (after fix) | PASS: 5 files, 48 tests; `.vite-temp` stays empty |
| `pnpm test`, normal permissions | PASS: 48/48; no `.vite-temp` created |
| `pnpm exec tsc --noEmit -p .` | PASS |
| `pnpm build` | PASS |

NOT_RUN: macOS/Linux locally (the CI `web` job runs on Ubuntu; see the PR checks). E2E is not affected and was not run.

## ES

**Causa.** Antes de ejecutar pruebas, Vite empaqueta `vite.config.ts` en un temporal dentro de `node_modules/.vite-temp/`. Si esa carpeta no admite escritura (bloqueo de antivirus o indexador, sandbox o permisos), Vitest termina con `EPERM`. Es el fallo de la auditoría Codex (R-05, AUD-005). Que fuera intermitente explicaba por qué parecía «transitorio», pero nunca se había identificado la causa.

**Reproducción.** En un worktree desechable se deniega la escritura solo sobre su propia `node_modules/.vite-temp` (comandos arriba): `pnpm exec vitest run` falla con `EPERM`. Después se restaura el permiso.

**Corrección.** Nuevo `vitest.config.ts` mínimo (alias `@` y patrón de pruebas). `pnpm test` usa `--configLoader runner`, que carga la configuración en memoria y no escribe en `.vite-temp`. `vite.config.ts` de Figma Make queda intacto.

**Resultado.** Con la carpeta bloqueada: 48/48 PASS y `.vite-temp` vacía. Con permisos normales: 48/48 PASS. `tsc` y `build` PASS. No ejecutado en local: macOS/Linux (lo cubre el job `web` del CI en Ubuntu).
