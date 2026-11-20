# F1 RBAC matrix / Matriz RBAC F1

**Status / Estado:** `VERIFIED_RUNNING` locally for the F1 routes at `dev` `c4e385c` (2026-11-19). The route and permission tables were read from the code (`authz.py`, routers, `seed.py`, `contracts/openapi.json`). Section 3 says, cell by cell, which assertions live in `test_rbac_matrix.py`, which ones are covered by other suites and which ones are still untested. Local PostgreSQL 16 + pgvector with synthetic data only; this is not a CI or deployment certification. / Comprobado en local para las rutas F1. La sección 3 distingue, celda a celda, lo que comprueba `test_rbac_matrix.py`, lo que cubren otras suites y lo que sigue sin probar. No es una certificación de CI ni de despliegue.

All paths below are under `/api/v1`, except `/health`. / Todas las rutas cuelgan de `/api/v1`, salvo `/health`.

## 1. Permissions by profile / Permisos por perfil

Authorization is **role + scope** (`Principal.can`, `Principal.require`, `Principal.scopes_for`). The UI never replaces a server check. / La autorización es **rol + ámbito**; la interfaz nunca sustituye la comprobación en servidor.

| Profile / Perfil | `applications.read` | `applications.crm` | `calls.aggregate` | `audit.read` | Scope in the seed / Ámbito en el seed |
| --- | --- | --- | --- | --- | --- |
| Admin / Administración | Yes (`*`) | Yes (`*`) | Yes (`*`) | Yes (`*`) | Global |
| Captación | Yes | Yes | Yes | No | One program per account (`P-IA`, `P-DATA`) |
| Selección | Yes | Yes | Yes | No | One call (`CONV-IA-2027A`) |
| Coordinación | No | No | Yes | No | Global (aggregates only) |
| Docente / Teacher | No | No | No | No | Cohorts (`COH-IA`, `COH-DATA`); only the KAN-128 requirement exceptions use them (see §4) |
| Aspirante / Applicant | No | No | No | No | No role; person-linked account |
| Coder / Learner | No | No | No | No | No role; person-linked account |

## 2. Endpoint, action and scope / Ruta, acción y ámbito

`✓` allowed · `scope` allowed only inside the assigned program or call (otherwise 403 with an explanatory message, see §4) · `401` no valid session · `403` no permission. / `✓` permitido · `scope` solo dentro del programa o la convocatoria asignados (si no, 403 con un mensaje explicativo, ver §4) · `401` sin sesión válida · `403` sin permiso.

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

Legend / Leyenda: **M** = asserted by `api/tests/test_rbac_matrix.py` (new or extended in this PR / nueva o ampliada en esta PR) · **E** = covered by an existing suite (named) / cubierta por una suite existente · **P** = pending, not tested / pendiente, sin prueba.

### 3.1 Cell coverage / Cobertura por celda

| Endpoint | Status for all 7 profiles + anonymous / Estado HTTP | Content and scope / Contenido y ámbito | Where / Dónde |
| --- | --- | --- | --- |
| `GET /health`, `GET /calls` | **M** (200 without session) | **E** public routes ignore unusable credentials | `test_rbac_matrix.py::test_public_routes_need_no_session`; `test_public_routes_auth.py::test_public_routes_work_with_no_or_unusable_credentials` |
| `POST /auth/login` | **M** new: 200 with each profile's credentials; 401 for an unknown account | **E** generic answer, no user enumeration, one session per success, failed login audited without identifiers | `test_rbac_matrix.py` (`login`); `test_auth.py`; `test_public_routes_auth.py`; `test_crm_audit.py::test_failed_login_is_audited_without_identifiers` |
| `POST /auth/logout` | **M** new: 204 for every profile, then `/auth/me` and a second logout give 401; anonymous 401 | **E** only the current session is revoked | `test_rbac_matrix.py::test_logout_ends_only_a_valid_session`; `test_auth.py::test_logout_revokes_only_current_session` |
| `POST /applications` (bearer optional) | **M** new: 201 for anonymous and every profile | **E** anonymous author, no account or role created, revoked session treated as anonymous | `test_rbac_matrix.py` (`create_application`); `test_public_routes_auth.py` |
| `GET /auth/me` | **M** | **E** roles and enrollments come from the same person | `test_rbac_matrix.py` (`me`); `test_rbac.py::test_coder_and_aspirant_states_come_from_the_same_person` |
| `GET /me/applications` | **M** | **M** new: aspirante and coder get exactly their own person's applications and no seed application of another person; staff get `[]`. **E** query parameters cannot redirect it and internal notes do not leak | `test_rbac_matrix.py::test_person_accounts_see_only_their_own_applications`; `test_rbac_regression.py::test_self_view_cannot_be_redirected_to_another_person_or_leak_notes` |
| `GET /applications` (list) | **M** | **M** new: captación only its program, selección only its call, admin both programs; the foreign application id is absent; `call_id`/`q` filters cannot bring it in. **E** totals per scope | `test_rbac_matrix.py::test_lists_contain_only_applications_inside_the_scope`, `::test_query_parameters_cannot_bring_foreign_applications_into_a_scoped_list`; `test_rbac.py`; `test_rbac_regression.py::test_query_parameters_cannot_broaden_scope_or_expose_foreign_aggregates` |
| `GET /applications/{id}` own scope / other scope | **M** both (`detail_own`, `detail_other`) | **E** reading writes `application.viewed` | `test_rbac_matrix.py`; `test_crm_audit.py` |
| `POST /applications/{id}/events` own scope / other scope | **M** both; `event_other` is new (403 for scoped staff and everyone else, 201 for admin) | **E** a rejected foreign write leaves no event and no success audit row; author derived by the server | `test_rbac_matrix.py`; `test_rbac_regression.py::test_foreign_crm_write_has_no_event_or_success_audit_side_effect`, `::test_crm_actor_is_server_derived_even_with_forged_payload` |
| `GET /calls/{id}/summary` own / other | **M** both | **E** small groups suppressed; filters cannot expose foreign aggregates | `test_rbac_matrix.py`; `test_rbac.py::test_coordinacion_gets_only_suppressed_aggregates`, `::test_small_groups_are_fully_suppressed` |
| `GET /audit-events` | **M** | **E** append-only | `test_rbac_matrix.py`; `test_crm_audit.py::test_audit_trail_is_append_only` |
| Invalid, revoked or deactivated sessions on every protected route | — | **E** | `test_rbac_regression.py`; `test_public_routes_auth.py::test_every_non_public_operation_answers_401_without_usable_credentials` |

A mutation check was run locally: removing the scope filter from `GET /applications` makes the four new content tests fail while the status-only test still passes, which is the gap the review pointed out. / Comprobación de mutación: sin el filtro de ámbito del listado fallan las cuatro pruebas de contenido nuevas y la de estados sigue pasando.

### 3.2 Still pending / Pendiente

- Out-of-scope access: **decided and tested** (§4): `test_rbac_matrix.py::test_out_of_scope_access_explains_itself_and_is_audited_without_side_effects`, `::test_profiles_without_application_access_get_403_for_known_and_unknown_ids`, `test_api_errors.py::test_403_keeps_detail_and_adds_request_id`. / Decidido y probado.
- **P:** Denied-attempt auditing covers `GET /applications/{id}` and `POST /applications/{id}/events`; requirement and pre-selection routes do not audit denials yet. / Las rutas de requisitos y preselección aún no auditan los intentos denegados.
- **P:** The requirement endpoints added after F1 (`/calls/{id}/requirements`, `/applications/{id}/requirement-reviews…`, `/applications/{id}/requirement-prefilter`) are **not** cells of this matrix. They have their own positive/negative scope tests in `test_call_requirements.py`, `test_requirement_reviews.py` and `test_requirement_prefilter.py`; adding them to section 2 is follow-up work. / Las rutas de requisitos posteriores a F1 no están en esta matriz; tienen sus propias pruebas.
- **P:** No rate-limit or brute-force test for `POST /auth/login`. / Sin prueba de límite de intentos.

### 3.3 Local result / Resultado local

At `dev` `c4e385c` merged into this branch: `test_rbac_matrix.py` **29 passed**; full API `pytest` **361 passed**. / `test_rbac_matrix.py`: 24 pruebas superadas.

## 4. Observations and gaps / Observaciones y brechas

- **EN — PO decision 19/11/2026, implemented:** an application outside the caller's scope answers `403` with a plain message ("belongs to a call you are not assigned to; ask administration for access"), and the denied attempt is written to the audit log as `application.access_denied` with the application id, code and permission only. An unknown id answers `404`. A profile without the permission in any scope gets `403` before any lookup, so it cannot tell known from unknown ids. The PO chose usefulness for staff plus audit over hiding existence (ids are random and only internal staff can ask). **ES — Decisión PO 19/11/2026, implementada:** fuera de ámbito responde `403` con un mensaje que explica el motivo y qué hacer, y el intento denegado queda en auditoría (`application.access_denied`, solo id, código y permiso). Un id inexistente da `404`. Sin el permiso en ningún ámbito, `403` antes de buscar.
- **EN:** `GET /calls/{id}/summary` answers `404` for an unknown call before checking permission. Call ids are public through `GET /calls`, so nothing new is disclosed. **ES:** El `404` previo al permiso no revela nada nuevo.
- **EN:** The seven profiles are the five staff roles plus applicant and learner. Since F1, `dev` adds `requirements.read`, `requirements.exception` (captación, selección, coordinación, docente) and `requirements.review` (captación, selección), see `authz.py`; they are documented by the KAN-128/KAN-135 reports, not in section 1. Teacher and learning permissions, admission decisions and staff invitation are not implemented. This PR does not change any permission. **ES:** Desde F1, `dev` añade permisos de requisitos (ver `authz.py` y los informes KAN-128/KAN-135). Faltan permisos de docencia, decisión de admisión e invitación de personal. Esta PR no cambia ningún permiso.
- **EN:** `audit.read` is granted only through the admin wildcard; any new role needs an explicit grant. **ES:** `audit.read` solo llega por el comodín de administración.
- **EN:** Every new endpoint must be added to section 2 with positive and negative scope tests. **ES:** Cada ruta nueva se añade a la sección 2 con pruebas positivas y negativas de ámbito.
