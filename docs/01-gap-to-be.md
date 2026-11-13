# 01 · Análisis GAP frente al TO-BE y reutilización

## GAP por objetivo

| Objetivo | Existe (antes de F1) | Falta para el 4/12 | Fase |
|---|---|---|---|
| O1 Centralización / CRM | Ficha local de candidatura | `Person` único, `Application` por convocatoria, CRM con autor y fecha, deduplicación, auditoría servidor | **F1** (base) · F2 |
| O2 Automatización 70 % | Nada | Inventario AS-IS etiquetado, tareas elegibles automatizadas (validación, faltantes, convocatoria/recordatorio), eventos medibles, ≥100 casos sintéticos, informe reproducible | F2 · F5 |
| O3 Competencias / portfolios | Catálogo, rúbricas, evaluaciones, analítica locales | Persistencia por cohorte, `Enrollment` desde decisión, `PortfolioLink`, permisos por cohorte | F3 |
| O4 Asistente RAG | 3 Q/A fijas | Corpus autorizado por ámbito, chunking, pgvector, filtro por permiso previo a la recuperación, citas, abstención, banco de 20–30 preguntas y métricas | F4 |
| O5 Riesgo de abandono | Regla + planes de apoyo | Dataset sintético, Dummy + LogisticRegression, model card, señales explicables, alerta → intervención revisada | F4 |
| O6 Feedback asistido | Revisión manual con rúbrica | Borrador desde tests precomputados + rúbrica, etiquetado y publicado solo tras revisión | F4 |
| O7 Dashboards y permisos | Dashboards por rol en cliente | RBAC rol+ámbito en API (**F1**), agregados calculados en servidor y suprimidos (F1 parcial · F5) | F1 · F5 |

## Reutilización priorizada

1. **Conservar sin reescribir:** `actions.ts`, `analytics.ts`, `domain.ts`, `components/{Modal,charts,ReviewModal,AttendanceModal}`, vistas académicas. Su lógica pura puede portarse al servidor o seguir sobre datos de la API.
2. **Adaptar detrás del conmutador de datos** (`src/shared/api/config.ts`): `Aspirant.tsx` y `Applications.tsx` → API (**hecho en F1** con vistas paralelas, sin borrar las locales); `Shell.tsx` → sesión y roles reales en modo servidor (**hecho**).
3. **Sustituir la lógica, no la vista:** `Assistant.tsx` → RAG; `applyAbsenceRule` se conserva como señal explicable junto al modelo.
4. **Corregir:** firmante de admisión (F2), etiquetas «IA» engañosas (F4), agregados de Coordinación en servidor (F5).
5. **No hacer:** migración a Next.js, microservicios, agentes, Qdrant/Chroma, HubSpot en vivo, ejecución de código arbitrario.
