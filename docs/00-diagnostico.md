# 00 · Diagnóstico verificable del estado actual

Fecha: 8 nov 2026 · Rama base: `main` (commit `85038e5`) · Revisión **ejecutada**, no solo estática.

## Evidencia ejecutada (CONFIRMADO)

| Comprobación | Resultado |
|---|---|
| `pnpm test` (Vitest 5.1) | 16/16 pasan (`migrate.test.ts`, `flows.test.ts`) |
| `tsc --noEmit` | sin errores |
| `pnpm build` | correcto; bundle 673 kB (180 kB gzip), aviso de chunk > 500 kB |
| Tamaño | 34 ficheros TS/TSX, 5.763 líneas, todo bajo `src/gistar/` |
| Navegador | 36 combinaciones rol × vista sin excepciones (recorrido CDP; ahora versionado en `e2e/local-mode.mjs`) |
| Entorno backend | Python 3.13; FastAPI 0.162, SQLAlchemy 2.1, Alembic 1.20, psycopg 3.3 instalables; PostgreSQL 16.2 + pgvector 0.6.2 ejecutables en el sandbox; Docker no disponible en el sandbox |
| Restricción Make | `vite.config.ts` y `.figma/make/*` los gestiona la plataforma y esperan la web en la raíz |

## Qué hay realmente

| Capacidad | Estado | Evidencia |
|---|---|---|
| 7 perfiles y navegación | Operativo **solo en el navegador**; permiso = comprobación de UI (`canOpen`); selector libre «Ver como» | `config.ts`, `Shell.tsx` |
| Persistencia | `localStorage` (`gistar-demo-v2`) con migración v1→v2; mononavegador | `store.tsx`, `migrate.ts` |
| Inscripción | **Simulada**: edita la candidatura fija `A-001`; no crea expedientes | `views/Aspirant.tsx` |
| Candidaturas / selección | Parcial local: 14 semilla, estados lineales, recomendación, doble firma docente+fundación. Sin CRM, requisitos, cupos ni reserva | `views/Applications.tsx` |
| Persona → coder | **Inexistente**: `candidaturas` y `coders` son entidades separadas; admitir no matricula | `types.ts` |
| Competencias, rúbricas versionadas, revisión en modal, historial, asistencia por sesión, calendario, analítica | **Operativo local** con pruebas de dominio (lo más reutilizable) | `actions.ts`, `analytics.ts`, `domain.ts` |
| Asistente | **Simulado**: coincidencia literal de 3 preguntas | `views/Assistant.tsx` |
| Riesgo de abandono | **Regla explicable** (≥3 ausencias en 6 sesiones); no hay ML | `domain.ts · applyAbsenceRule` |
| Feedback IA | **Simulado**: el texto «propuesto por IA» es dato semilla | `seed.json` |
| Auditoría | Bitácora en cliente, editable por el usuario | `store.tsx` |
| GitHub / portfolio | **Simulado** (toast + URL ficticia) | `views/Deliveries.tsx` |
| API, autenticación, RBAC, BD, RAG, ML, medición 70 % | **Inexistentes** antes de F1 | — |

## Deuda técnica detectada

1. IDs generados en cliente (`Date.now`/random): colisionan al compartir datos.
2. Fecha de demo fija (`2026-11-02`) en lugar de reloj del servidor.
3. Privacidad de Coordinación calculada en el cliente, que recibe todos los datos nominales.
4. El rol «docente» firma decisiones de admisión; el TO-BE las asigna a selección/captación.
5. Etiquetas «IA» sobre contenido que no genera ningún modelo.
6. Las verificaciones de navegador no estaban versionadas (el script vivía en `/tmp`).
