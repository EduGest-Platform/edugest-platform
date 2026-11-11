# Incremento F1 · Cimientos compartidos

**Rama:** `f1-cimientos` (base `main@85038e5`, que queda intacta) · **Fecha:** 2026-11-08 · **Puerta:** 12/11

## Objetivo

Backend real (identidad, convocatorias, candidaturas, CRM, RBAC por ámbito, auditoría) y primera conexión de la web
(inscripción, candidaturas, mi candidatura y auditoría) sin alterar el comportamiento del prototipo en modo local.

## Modificaciones

### Código existente (cambios acotados)

| Fichero | Cambio | Motivo |
|---|---|---|
| `src/App.tsx` | Envuelve la app con `ApiSessionProvider` | Sesión API disponible para el Shell; inerte en modo local |
| `src/gistar/Shell.tsx` | En modo servidor: pantalla de acceso, «Actuar como» limitado a roles asignados por la API, botón Salir, vistas `API_SCREENS` y aviso en vistas aún locales. En modo local, sin cambios visibles | Roles reales, no selector libre |
| `package.json` | Dependencias `openapi-fetch` y (dev) `openapi-typescript`; scripts `gen:api`, `e2e:local`, `e2e:api` | Cliente tipado generado del contrato |
| `src/vite-env.d.ts` | Añade el tipo de `VITE_GISTAR_API_URL` (se conserva la referencia original) | Tipado del conmutador |
| `.gitignore` | Entradas Python (`.venv`, `__pycache__`, `.pytest_cache`, `*.egg-info`) | — |

No se ha modificado ninguna lógica de `src/gistar/` (store, dominio, acciones, analítica ni vistas locales).

### Código nuevo

| Ruta | Contenido |
|---|---|
| `api/app/core/` | `config` (GISTAR_*), `db`, `security` (scrypt, token opaco), `authz` (Principal, permisos rol+ámbito), `audit`, `deps`, `text` |
| `api/app/modules/identity` | `Person`, `User`, `RoleAssignment`, `AuthSession`; `/auth/login`, `/auth/me`, `/auth/logout` |
| `api/app/modules/catalog` | `Program`, `Call`, `Cohort`; `GET /calls`, `GET /calls/{id}/summary` (agregados suprimidos) |
| `api/app/modules/admissions` | `Application`, `ApplicationEvent`; inscripción con deduplicación y código por convocatoria (bloqueo de fila), listados filtrados por ámbito, ficha, eventos CRM, `/me/applications` |
| `api/app/modules/learning` | `Enrollment` (misma `Person` → cohorte) |
| `api/app/modules/audit` | `AuditEvent` + `GET /audit-events` (admin) |
| `api/alembic/versions/0001_f1_cimientos.py` | Esquema completo + trigger de solo inserción en `audit_event` |
| `api/app/seed.py` | Carga `src/gistar/seed.json` (fuente única de datos sintéticos): 2 programas, 4 convocatorias, 2 cohortes, 34 personas, 12 candidaturas, 20 matrículas, 8 cuentas |
| `api/tests/` | 27 pruebas pytest sobre PostgreSQL |
| `contracts/openapi.json` · `src/shared/api/schema.gen.ts` | Contrato y tipos generados |
| `src/shared/api/` | `config` (conmutador), `client` (openapi-fetch + token por pestaña), `session` (login, me, mapeo de roles) |
| `src/gistar/views/api/ApiAdmissions.tsx` | Inscripción, mi candidatura, expedientes con ficha CRM en modal, auditoría del servidor |
| `src/gistar/components/LoginScreen.tsx` | Acceso con cuentas sintéticas e inscripción pública |
| `e2e/` | Arnés CDP sin dependencias, `f1-api-mode.mjs`, `local-mode.mjs` |
| `infra/compose.yaml`, `api/Dockerfile`, `.github/workflows/ci.yml`, `.env.example`, `api/.env.example` | Entorno reproducible y CI |
| `docs/` | Diagnóstico, GAP, arquitectura, plan, ADR 0001–0004, este registro |

## Evidencia de verificación (ejecutada en el sandbox)

| Comprobación | Resultado |
|---|---|
| `tsc --noEmit` | OK |
| `pnpm test` (Vitest) | 16/16 (sin regresiones) |
| `pnpm build` | OK (modo local y modo servidor) |
| `alembic upgrade head` → `downgrade base` → `upgrade head` → `alembic check` | OK, sin deriva |
| `pytest` sobre PostgreSQL 16.2 | **27/27**, sin avisos de deprecación propios |
| Contrato | `contracts/openapi.json` y `schema.gen.ts` regenerados sin diferencias; prueba de deriva incluida |
| `e2e/f1-api-mode.mjs` (2 contextos de navegador aislados, API + PostgreSQL) | **13/13** |
| `e2e/local-mode.mjs` (preview de Make, modo local) | **4/4** (36 combinaciones rol×vista, migración v1→v2, sin UI de servidor) |

Cobertura de pytest: login y credenciales genéricas, sesión caducada, logout por sesión; inscripción pública con
persona + evento + auditoría sin datos personales; duplicado normalizado → 409; reutilización de persona entre convocatorias;
validaciones (consentimiento, correo, longitud, convocatoria cerrada o inexistente); aspirante ve solo su vista mínima;
**6 inscripciones concurrentes con códigos únicos**; 401 sin sesión; admin ve todo; captación limitada a su programa (lectura, CRM y filtros);
selección limitada a su convocatoria; docente, aspirante y coder sin acceso a expedientes ni auditoría; coordinación solo agregados con
supresión de celdas y grupos pequeños; eventos CRM con autor y auditoría sin texto libre; CRM no permite cambiar etapa;
auditoría inmutable (UPDATE/DELETE fallan); login fallido auditado sin identificadores; contrato al día y seguridad declarada en todos los endpoints privados.

E2E en modo servidor: acceso; captación IA solo ve CONV-IA; inscripción pública desde otro navegador con código; duplicado rechazado en UI;
el primer navegador ve la nueva candidatura (persistencia compartida); evento CRM con autor; captación Data no la ve;
aviso de vista local; docente recibe 403 de la API; coordinación sin candidaturas y rol fijado por el servidor; auditoría sin datos personales;
la sesión de una pestaña no se ve afectada por los inicios y cierres de la otra; sin excepciones JS.

## Cómo reproducir

```bash
# API
cd api && python -m venv .venv && . .venv/bin/activate && pip install -e ".[dev]"
export GISTAR_DATABASE_URL=postgresql+psycopg://gistar:gistar@localhost:5432/gistar
alembic upgrade head && python -m app.seed --reset
GISTAR_CORS_ORIGINS='["http://127.0.0.1:4173"]' uvicorn app.main:app --port 8000 &
GISTAR_TEST_DATABASE_URL=postgresql+psycopg://gistar:gistar@localhost:5432/gistar_test pytest
# Web en modo servidor + E2E
cd .. && VITE_GISTAR_API_URL=http://127.0.0.1:8000 pnpm exec vite build --outDir /tmp/webdist
(cd /tmp/webdist && python3 -m http.server 4173 &) && pnpm e2e:api
WEB_URL=http://localhost:5173/ pnpm e2e:local   # con `pnpm dev` en modo local
```

## No verificado / límites conocidos

- **`infra/compose.yaml` y `api/Dockerfile` no se han ejecutado** (Docker no disponible en el sandbox). **El workflow de CI no se ha ejecutado** en GitHub.
- La preview de Figma Make sigue en modo local: no hay backend accesible desde ella. El modo servidor se demuestra en local o en un despliegue propio.
- Las cuentas comparten una contraseña de demostración documentada; no hay límite de intentos ni recuperación de contraseña.
- Las personas que se inscriben por el formulario no reciben cuenta (activación por invitación en F2).
- El 409 de duplicado permite inferir si un correo ya está inscrito (aceptado para la demo, ver riesgos).
- Las vistas académicas, el asistente y las alertas siguen con datos locales; los KPI del inicio en modo servidor proceden de esos datos locales (señalado en pantalla).
- Los cambios de etapa, valoración, decisión y matrícula desde decisión corresponden a F2.

## Siguiente incremento (F2, 13–18/11)

`RequirementReview` y requisitos configurables por convocatoria · puntuación con rúbrica versionada · `AdmissionDecision`
con firmantes (selección + captación) y justificación · cupos y lista de espera · `Enrollment` desde la decisión ·
eventos medibles para el 70 % · migrar `Applications.tsx` (flujo de revisión) al modo servidor y retirar la doble firma del rol docente.
