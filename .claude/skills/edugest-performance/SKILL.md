---
name: edugest-performance
description: Keep the EduGest web app fast and light to load. Use when adding screens, libraries, charts or images, and before the freeze.
---

# EduGest performance

Goal: the app loads fast on a modest laptop or phone and a slow connection.

## Rules

- Do not add a library for something a few lines of code can do. Ask the team before adding any dependency.
- Load big screens only when they are opened: `React.lazy(() => import('./views/X'))` with a `Suspense` fallback that uses the app's loading text. Coders should not download admin dashboards.
- Charts: keep using `src/gistar/components/charts.tsx`. Do not add a chart library.
- Icons: import single icons from `lucide-react` (`import { Search } from 'lucide-react'`), never the whole set.
- Images: WebP or AVIF, with `width` and `height` set so the page does not jump.
- Do not fetch the same data twice on one screen. Do not refetch in a loop; refresh on focus or on a user action (as `ApiApplications` does).

## Check the size

After `pnpm build`, look at the size of `dist/assets/index-*.js` in the output (today about 440 kB, 124 kB gzip). If a change makes it grow a lot, say why in the PR.

## Before the freeze (S3)

- Lighthouse on the public page: performance 90 or more, no layout shift.
- Check the slowest screen (GroupAnalytics) on a throttled connection in DevTools.
