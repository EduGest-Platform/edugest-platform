---
name: edugest-frontend-conventions
description: Rules for any change to the EduGest web app (React 19, Vite 8, TypeScript, Tailwind v4 in src/). Use before writing or changing frontend code, components, screens or the API client.
---

# EduGest frontend conventions

The base skill for frontend work. The other frontend skills build on it.

## Stack (do not change)

- React 19, Vite 8, TypeScript, Tailwind v4. Styles and colour tokens live in `src/index.css` (`navy`, `blue`, `teal`, `gold`, `ink`, `muted`, `line`, `mist`, `canvas`).
- The web app lives at the repo root (ADR-0001): `index.html`, `vite.config.ts`, `src/`.
- Keep `.figma/`, `vite.config.ts` and the aliases. A Vite preview may already be running (Figma Make).
- Never migrate to Next, Astro or another framework.

## Where things go

| What | Where |
|---|---|
| Screens | `src/gistar/views/` |
| Screens that use the real API | `src/gistar/views/api/` |
| Shared parts | `src/gistar/components/` and `src/gistar/ui.tsx` (`Button`, `Card`, `Notice`, `Status`, `Field`, `Table`, `Empty`) |
| Pure logic (no React) | `src/gistar/*.ts`, with tests in `src/gistar/__tests__/` |
| API client and session | `src/shared/api/` |
| Local demo data | `src/gistar/seed.json` (shared with the API seed: do not change it for frontend-only demos) |

Reuse `ui.tsx` before creating a new component. Use the existing colour families of `Status` and `Notice`, so new screens look like the rest of the app.

## Code

- Code, names, files and tests in English. Text shown to people in Spanish.
- Small components and single-purpose functions. Readability over cleverness. Comments in plain English that say *why*.
- API types come from `contracts/openapi.json` with `pnpm gen:api`. Never write them by hand.
- Put rules (statuses, calculations) in a pure `.ts` file with unit tests, not inside the component.

## Data honesty

- Two modes: local (localStorage, synthetic) and API (`VITE_GISTAR_API_URL`). Keep them separate (`src/shared/api/config.ts`).
- Never show mock or invented data as if it came from the server. If the API does not send something yet, say so on screen. Local examples carry a visible label ("Ejemplo local").
- Synthetic data only. Never real student data.
- AI and risk results are always suggestions. A person decides admissions (no automatic rejection).

## Public pages and SEO (landing, catalogue only)

- A `<title>` and short description per public page, `lang="es"`, one `h1`, clear headings.
- Pages behind the login must not be indexed (`noindex`).

## Before a PR

Run and paste the results in the PR:

```bash
pnpm exec tsc --noEmit -p tsconfig.json
pnpm test
pnpm build
pnpm exec oxfmt --check src e2e   # warning only for now; do not reformat files you did not change
```

Also: the screen works with the keyboard, and you say clearly what you did not check (for example "not checked in a browser with the API").
