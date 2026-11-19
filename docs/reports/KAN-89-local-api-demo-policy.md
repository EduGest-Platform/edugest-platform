# KAN-89 — Local/API isolation and demo policy / Aislamiento local/API y política de demo

Base: `dev` at `6a55b66`. Builds on [ADR-0004](../adr/0004-conmutador-local-api.md). Synthetic data only; no secret appears here.

## EN

### What changed in code

- `src/shared/api/config.ts`: `dataSourceFor(view)` is the **single rule** for where a view gets its data. It returns `'local'` for every view when `VITE_GISTAR_API_URL` is unset, and `'api'` only for views in `API_VIEWS` when it is set.
- `src/gistar/apiScreens.ts`: the API screens registry moved out of `Shell.tsx`. `Shell.tsx` now picks the screen and the "local data" banner from `dataSourceFor`, so both come from one place.
- `src/gistar/__tests__/data-source.test.ts` (5 tests) covers:
  - local mode is local for every menu view;
  - API mode uses the API exactly for `API_VIEWS`;
  - unknown views fall back to local;
  - every `API_VIEWS` entry is a real view and has an API screen, and no local view does.
  Mutation check: removing `auditoria` from the registry makes the last test fail.

Before this change, `API_VIEWS` (banner) and the screen map in `Shell.tsx` were two separate lists. If they drifted, a view could silently show local data in API mode **without** the "local data" banner. The test now blocks that.

### Demo policy

| Situation | Mode | Rule |
|---|---|---|
| Figma Make preview, design reviews | Local (no `VITE_GISTAR_API_URL`) | Prototype only: UI-level permissions, data in `localStorage`, "Restablecer" resets it. Never presented as persisted data or real security. |
| Defence demo (10 Dec), rehearsal (9 Dec), staging | API (`VITE_GISTAR_API_URL` set) | Admissions, CRM and audit come from FastAPI with server-side role/scope checks. Views not migrated yet show the "local demo data" banner; never claim they are persisted. |
| Any mode | — | Synthetic data only. Demo accounts use `GISTAR_DEMO_PASSWORD` from the environment (blocked in staging/production by KAN-101); never written in slides, docs or tickets. |
| Any mode | — | A single view never mixes local and API data (ADR-0004). A view moves to API only when its whole flow is migrated: add it to `API_VIEWS` **and** `API_SCREENS` in the same PR (the test enforces it). |
| API unreachable during a demo | API | The login shows "No se puede conectar con la API"; do not switch to local mode live to hide it. Restart the backend (`/health` must answer `ok`) or explain the fallback openly. |

### Evidence (Windows 10, Node 24.18.0, pnpm 10.34.3)

| Check | Result |
|---|---|
| `pnpm test` | PASS: 6 files, 53 tests (48 existing + 5 new) |
| `pnpm exec tsc --noEmit -p .` | PASS |
| `pnpm build` | PASS |

NOT_RUN locally: browser E2E (`e2e/local-mode.mjs`, `e2e/f1-api-mode.mjs`). For the API-mode browser flow, see the PR checks (`registration` job). No business logic, API contract or migration changed.

## ES

**Código.** `dataSourceFor(view)` es la regla única del origen de datos de cada vista: sin `VITE_GISTAR_API_URL`, todas las vistas son locales; con ella, solo usan la API las de `API_VIEWS`. El registro de pantallas API se mueve a `src/gistar/apiScreens.ts`, y `Shell.tsx` decide pantalla y aviso con la misma regla. Cinco pruebas Vitest impiden que `API_VIEWS` y las pantallas API diverjan. Antes podía mostrarse una vista con datos locales en modo API sin el aviso.

**Política de demo.**
- Preview de Make: modo local, solo prototipo; permisos de interfaz y datos en el navegador.
- Defensa, ensayo y staging: modo API. Las vistas aún no migradas muestran el aviso de datos locales y nunca se presentan como persistidas.
- Siempre datos sintéticos. La contraseña demo sale de `GISTAR_DEMO_PASSWORD` y nunca se escribe en diapositivas, documentos ni tickets.
- Una vista nunca mezcla fuentes. Migrar una vista exige añadirla a `API_VIEWS` y a `API_SCREENS` en el mismo PR; la prueba lo exige.
- Si la API cae durante la demo, no se cambia a modo local para ocultarlo: se reinicia el backend o se explica abiertamente.

**Evidencia.** Vitest 53/53, `tsc` y `build` PASS en Windows. No ejecutado en local: E2E de navegador (ver checks del PR).
