feat(api): decisión de selección que crea la matrícula (S2)

## Qué hace

Añade la decisión humana que cierra la selección y, al admitir, crea la matrícula en la misma transacción. Hasta ahora `Enrollment` solo se creaba en `seed.py`, así que el recorrido aspirante → coder no se sostenía fuera de la demo.

- `POST /api/v1/applications/{id}/selection-decisions`: `admitida` (con `cohort_id`, crea la matrícula), `lista_espera` o `no_admitida`.
- `GET /api/v1/applications/{id}/selection-decisions`: historial con quién, cuándo y por qué.
- Tabla `selection_decision` (migración `0010`), de solo adición, con el mismo patrón que `preselection_decision`.
- Permisos `selection.read` y `selection.decide` para selección y coordinación (decisión PO 19/11); administración por el comodín. Captación y docente no los tienen.
- Texto fijo en el CRM y auditoría sin texto libre: el motivo solo vive en `selection_decision`.

Reglas, respuestas de error y límites: `docs/reports/selection-decision-enrollment.md`.

## Qué no hace

- Una sola decisión humana; el número de firmas no está confirmado por la fundación.
- No envía correos (KAN-50) ni invita al coder al matricularlo (D2).
- Sin interfaz web: la selección sigue en modo local.
- No permite corregir una decisión ya tomada.

## Pruebas ejecutadas

- `pytest` completo: 744 pasan (34 nuevos en `test_selection_decisions.py`), con PostgreSQL 16 + pgvector.
- Incluye pruebas de rollback si falla la auditoría, de dos admisiones simultáneas con una sola plaza y de permisos por perfil y por ámbito.
- `alembic check` sin deriva; `ruff` sin errores; contrato OpenAPI y `schema.gen.ts` regenerados.
- `tsc --noEmit` y Vitest (67) en verde.
- No ejecutado: `pnpm build`, E2E, gitleaks y el job `compose` (sin Docker en mi entorno).

## Al integrar

- Si otro PR añade una `0010`, renumerar este fichero y su `revision`.
- Si cambia `contracts/openapi.json`, volver a ejecutar `pnpm gen:api`.
- Añadir `selection_decision` al diagrama ER de admisiones cuando se integre.
