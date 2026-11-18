# F1 RBAC matrix / Matriz RBAC F1

**Status / Estado:** `VERIFIED_RUNNING` for the code at `dev` `8481d08` (2026-11-18). The route and permission tables below were read from the code (`authz.py`, routers, `seed.py`, `contracts/openapi.json`); the 39 RBAC, matrix, regression and CRM/audit tests passed locally on PostgreSQL 16.2 + pgvector 0.6.2, including `test_rbac_matrix.py`, which asserts every cell of section 2. This is not a CI or deployment certification. / Las tablas se han leído del código y las 39 pruebas de RBAC, matriz, regresión y CRM/auditoría pasaron en local; `test_rbac_matrix.py` comprueba cada celda de la sección 2. No es una certificación de CI ni de despliegue.

All paths below are under `/api/v1`, except `/health`. / Todas las rutas cuelgan de `/api/v1`, salvo `/health`.

## 1. Permissions by profile / Permisos por perfil

Authorization is **role + scope** (`Principal.can`, `Principal.require`, `Principal.scopes_for`). The UI never replaces a server check. / La autorización es **rol + ámbito**; la interfaz nunca sustituye la comprobación en servidor.

| Profile / Perfil | `applications.read` | `applications.crm` | `calls.aggregate` | `audit.read` | Scope in the seed / Ámbito en el seed |
| --- | --- | --- | --- | --- | --- |
| Admin / Administración | Yes (`*`) | Yes (`*`) | Yes (`*`) | Yes (`*`) | Global |
| Captación | Yes | Yes | Yes | No | One program per account (`P-IA`, `P-DATA`) |
| Selección | Yes | Yes | Yes | No | One call (`CONV-IA-2027A`) |
| Coordinación | No | No | Yes | No | Global (aggregates only) |
| Docente / Teacher | No | No | No | No | Cohorts (`COH-IA`, `COH-DATA`); no endpoint uses them yet |
| Aspirante / Applicant | No | No | No | No | No role; person-linked account |
| Coder / Learner | No | No | No | No | No role; person-linked account |

## 2. Endpoint, action and scope / Ruta, acción y ámbito

`✓` allowed · `scope` allowed only inside the assigned program or call (otherwise 403) · `401` no valid session · `403` no permission. / `✓` permitido · `scope` solo dentro del programa o la convocatoria asignados (si no, 403) · `401` sin sesión válida · `403` sin permiso.

| Endpoint | Anonymous | Aspirante / Coder | Captación | Selección | Coordinación | Docente | Admin |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `GET /health` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `POST /auth/login` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `GET /calls` (offer data only) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `POST /applications` (bearer optional) | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `GET /auth/me`, `POST /auth/logout` | 401 | ✓ own session | ✓ | ✓ | ✓ | ✓ | ✓ |
| `GET /me/applications` | 401 | ✓ own person only | `[]` unless linked to a person | `[]` unless linked | `[]` unless linked | `[]` unless linked | `[]` unless linked |
| `GET /applications` (list) | 401 | 403 | scope (filtered) | scope (filtered) | 403 | 403 | ✓ all |
| `GET /applications/{id}` | 401 | 403 | scope | scope | 403 | 403 | ✓ |
| `POST /applications/{id}/events` | 401 | 403 | scope | scope | 403 | 403 | ✓ |
| `GET /calls/{id}/summary` (aggregates, small groups suppressed) | 401 | 403 | scope | scope | ✓ | 403 | ✓ |
| `GET /audit-events` | 401 | 403 | 403 | 403 | 403 | 403 | ✓ |

Server-side rules worth keeping / Reglas de servidor a conservar:

- The CRM author is the authenticated user, never a payload field. / El autor del CRM es el usuario autenticado, nunca un campo del cuerpo.
- Reading an application and viewing a call summary write an audit row (`application.viewed`, `call.summary_viewed`); adding an event writes `application.event_added`. Audit metadata carries no free text. / Consultar un expediente o un resumen escribe una fila de auditoría, sin texto libre.
- Query parameters (`call_id`, `stage`, `q`) can only narrow a list, never widen the scope. / Los parámetros solo estrechan el ámbito.

## 3. Tests that back the matrix / Pruebas que respaldan la matriz

| File | Covers / Cubre |
| --- | --- |
| `api/tests/test_rbac_matrix.py` | Executable copy of section 2: expected status for each profile and endpoint, plus `[]` for staff in `/me/applications`. If a permission changes, this test fails until the matrix is updated / Copia ejecutable de la sección 2 |
| `api/tests/test_rbac.py` | Anonymous 401; admin sees every call; program and call scopes; teacher without admissions; coordination aggregates with suppression; person accounts blocked from staff routes; audit admin-only |
| `api/tests/test_rbac_regression.py` | Invalid tokens; foreign CRM write without side effects; spoofed admin headers; query parameters cannot widen scope; revoked assignment and deactivated account on a live session; server-derived CRM actor; self-view cannot be redirected |
| `api/tests/test_crm_audit.py` | CRM events and their audit rows |

Local result at `dev` `8481d08`: **39 passed** (`test_rbac_matrix.py` 9, `test_rbac.py`, `test_rbac_regression.py` and `test_crm_audit.py` 30). / Resultado local: 39 pruebas superadas.

## 4. Observations and gaps / Observaciones y brechas

- **EN:** An out-of-scope staff user gets `403` for an existing application and `404` for an unknown id, which reveals that an id exists. Ids are random UUIDs, so the risk is low; decide whether to unify the answer. **ES:** Un id existente fuera de ámbito da `403` y uno inexistente `404`; el riesgo es bajo (UUID aleatorios), pero conviene decidir si se unifica.
- **EN:** `GET /calls/{id}/summary` answers `404` for an unknown call before checking permission. Call ids are public through `GET /calls`, so nothing new is disclosed. **ES:** El `404` previo al permiso no revela nada nuevo.
- **EN:** The seven profiles are the five staff roles plus applicant and learner. Teacher and learning permissions, admission decisions, staff invitation and requirement-review permissions are not implemented. **ES:** Los siete perfiles son los cinco roles internos más aspirante y coder; faltan permisos de docencia, decisión de admisión, invitación de personal y revisión de requisitos.
- **EN:** `audit.read` is granted only through the admin wildcard; any new role needs an explicit grant. **ES:** `audit.read` solo llega por el comodín de administración.
- **EN:** Every new endpoint must be added to section 2 with positive and negative scope tests. **ES:** Cada ruta nueva se añade a la sección 2 con pruebas positivas y negativas de ámbito.
