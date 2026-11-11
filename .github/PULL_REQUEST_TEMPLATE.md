<!-- Título / Title: feat|fix|test|docs: short English summary -->

## Qué cambia / What changes

<!-- Historia o ticket, y resumen en 2-3 frases. / Story or ticket, and a 2-3 sentence summary. -->

- Ticket/historia:
- Resumen:

## Tipo / Type

- [ ] `feat` — nueva funcionalidad / new functionality
- [ ] `fix` — corrección / bug fix
- [ ] `test` — pruebas / tests
- [ ] `docs` — documentación / documentation
- [ ] `chore` / infra

## Evidencia de pruebas / Test evidence

<!-- Comandos ejecutados y resultado real. Nada se marca Done sin evidencia (CONSTITUTION.md §E.6). -->
<!-- Commands actually run and their results. Nothing is Done without evidence. -->

| Comprobación / Check | Comando / Command | Resultado / Result |
|---|---|---|
| Typecheck | `pnpm exec tsc --noEmit -p tsconfig.json` | PASS / FAIL / NOT RUN |
| Web unit | `pnpm test` | PASS / FAIL / NOT RUN |
| API | `pytest` (en `api/`, con BD sintética local) | PASS / FAIL / NOT RUN / BLOCKED |
| E2E (si aplica / if relevant) | `pnpm e2e:local` · `pnpm e2e:api` | PASS / FAIL / NOT RUN |

## Contrato y migraciones / Contract and migrations

- [ ] No cambia el contrato / contract unchanged — **o** / **or**: `contracts/openapi.json` + `pnpm gen:api` regenerados en este PR
- [ ] No hay migraciones / no migrations — **o** / **or**: migración Alembic versionada, reversible y probada en BD local sintética

## Seguridad y RBAC / Security and RBAC

- [ ] Cambios sensibles a permisos incluyen 1 prueba positiva + 1 negativa (401/403, ámbito) / permission-sensitive changes include 1 positive + 1 negative authorization test
- [ ] Solo datos sintéticos; sin secretos, `.env` ni credenciales en el diff / synthetic data only; no secrets in the diff

## Checklist DoD (contribution.md)

- [ ] Un owner y una persona revisora distinta / one owner, a different reviewer
- [ ] Alcance pequeño y enfocado / small focused scope
- [ ] Documentación actualizada si procede (ES/EN) / docs updated where relevant (ES/EN)
- [ ] Bloqueos o pruebas no ejecutadas declarados arriba / blockers or not-run tests declared above

## Notas para revisión / Review notes

<!-- Riesgos, decisiones, capturas si hay UI. / Risks, decisions, screenshots for UI changes. -->
