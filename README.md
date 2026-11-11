# Gistar (nombre provisional) · Proyecto Final 2 · Fundación Somos F5

Plataforma para centralizar inscripción, preselección, selección, formación y acompañamiento.
**Datos exclusivamente sintéticos.** La IA asiste; las decisiones de admisión, exclusión o baja las toman personas.

| Parte | Tecnología | Dónde |
|---|---|---|
| Web | React 19 · Vite 8 · TypeScript · Tailwind 4 (en la raíz: así lo ejecuta Figma Make) | `src/` |
| API | FastAPI · SQLAlchemy 2 · Alembic · PostgreSQL 16 | `api/` |
| Contrato | OpenAPI → tipos TS generados | `contracts/`, `src/shared/api/` |
| Pruebas E2E | Chromium vía CDP (Playwright en F5) | `e2e/` |
| Infra | compose + CI | `infra/`, `.github/workflows/` |
| Documentación | diagnóstico, GAP, arquitectura, ADR, incrementos | `docs/` |

## Dos modos de la web

- **Local** (por defecto, el de la preview de Make): sin `VITE_GISTAR_API_URL`. Todo en `localStorage`, selector libre «Ver como».
- **Servidor**: `VITE_GISTAR_API_URL=http://localhost:8000 pnpm dev`. Login real, rol fijado por el servidor; inscripción,
  candidaturas/CRM y auditoría usan la API. El resto de vistas avisan de que siguen en local hasta su incremento.

## Comandos

```bash
pnpm install && pnpm dev          # web
pnpm test                         # Vitest (dominio web)
pnpm build                        # build de producción
pnpm gen:api                      # regenerar cliente TS desde contracts/openapi.json
pnpm e2e:local                    # regresión modo local (WEB_URL)
pnpm e2e:api                      # recorrido F1 con API (ver docs/incrementos/F1-cimientos.md)
```

API y PostgreSQL: ver [`api/README.md`](api/README.md); requieren `infra/.env` y `api/.env` locales (copiar de los `.env.example`, nunca se versionan). Estado y plan: [`docs/README.md`](docs/README.md).

## Gobierno del proyecto / Project governance

| Documento | Qué es / What it is |
|---|---|
| [`CONSTITUTION.md`](CONSTITUTION.md) · [ES](CONSTITUTION.es.md) | Constitución: principios y reglas fundamentales / Constitution: core principles |
| [`AGENTS.md`](AGENTS.md) | Instrucciones canónicas para agentes de IA / Canonical AI-agent instructions |
| [`CLAUDE.md`](CLAUDE.md) | Notas específicas para Claude / Claude-specific notes |
| [`contribution.md`](contribution.md) | Reglas de contribución humana / Human contribution rules |
| [`commands.md`](commands.md) | Comandos verificados y previstos / Verified and planned commands |
| [`projectplan.md`](projectplan.md) | Plan de producto y entrega / Product and delivery plan |

**EN summary:** Gistar (working name) is the Somos F5 Final Project 2 platform covering application, preselection, human-decided selection, enrolment and academic follow-up, with a scoped RAG assistant and advisory dropout ML. Synthetic data only; code in English; repository docs in Spanish and English. Start with the constitution, then `AGENTS.md` (agents) or `contribution.md` (humans).
