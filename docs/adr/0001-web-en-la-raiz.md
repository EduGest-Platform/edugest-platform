# ADR-0001 · Mantener la web React/Vite en la raíz del repositorio

**Estado:** aceptada (F1) · **Fecha:** 2026-11-08

**Contexto.** La propuesta v1.2 sugiere mover la web a `apps/web/`. Figma Make gestiona `vite.config.ts` y `.figma/make/*` y ejecuta, previsualiza y despliega la app desde la raíz.

**Decisión.** La web permanece en la raíz; el resto se añade en carpetas hermanas (`api/`, `contracts/`, `e2e/`, `infra/`, `docs/`). No se migra a Next.js.

**Consecuencias.** La preview de Make sigue funcionando sin cambios. Si el frontend deja de desplegarse con Make, se podrá mover a `apps/web/` con un único PR mecánico.
