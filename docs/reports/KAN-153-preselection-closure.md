# KAN-153 — End of pre-selection with audit / Fin de preselección con auditoría

Owner / responsable: Elizabeth. Reviewer / revisión: Yohanna. Prepared / fecha: 2026-11-18.
Status / estado: **implemented and tested locally; not merged** / implementado y probado en local; sin fusionar. Based on `dev` after KAN-128 and KAN-135 were integrated; migration chain 0004 → 0006 → 0005 / basada en `dev` tras integrar KAN-128 y KAN-135; cadena de migraciones 0004 → 0006 → 0005.

## ES — Qué implementa

Implementa las decisiones TO-BE de la PO registradas el 18/11/2026 en KAN-119 y KAN-153. **Son decisiones de diseño de producto, no un proceso validado por Melissa ni una práctica confirmada del AS-IS.**

| Decisión de la PO | Cómo queda en el código |
|---|---|
| Convocar a selección termina la preselección aunque los requisitos sigan en revisión | `convocada` se acepta desde `enviada` y `requisitos_en_revision`; las revisiones de requisitos (KAN-128) no la bloquean. La decisión guarda cuántas revisiones seguían sin resolver (`unresolved_requirement_reviews`). |
| Retirada expresa | `retirada_expresa` → etapa `retirada`, con actor, fecha y motivo. |
| Silencio: 30 días y 4 intentos por defecto, editables por convocatoria | Columnas `call.silence_days` y `call.silence_max_contacts` (valores por defecto 30 y 4). `PUT /calls/{id}/preselection-policy`. |
| El silencio solo crea una propuesta de revisión, nunca cierra solo | No hay temporizador ni cambio de etapa automático. `GET /calls/{id}/silence-review` calcula al consultar qué candidaturas han cumplido el umbral. |
| Cinco perfiles internos pueden confirmar o reprogramar, con permiso de acción y ámbito; aspirante y coder no | Permisos `preselection.read` y `preselection.decide` para administración, captación, selección, coordinación y docente. Se comprueban en servidor por convocatoria (o cohorte alimentada por la convocatoria). Las cuentas de persona reciben 403. |
| Registrar actor, fecha, motivo y evidencias de contacto | Tabla `preselection_decision` (append-only por convención) + evento CRM + evento de auditoría. Cada intento de contacto registra canal, fecha y **resultado** (`respondida` / `sin_respuesta`). |
| Cambiar la configuración no altera decisiones históricas | Cada decisión de silencio guarda una copia de la evidencia y de los umbrales usados. |
| Aceptación: 403 sin mutación fuera de ámbito, silencio sin cierre automático, requisitos abiertos no bloquean | Cubierto por `api/tests/test_preselection_closure.py`. |

### Endpoints (todos privados, con Bearer)

| Método y ruta | Permiso | Resultado |
|---|---|---|
| `POST /api/v1/applications/{id}/preselection-decisions` | `preselection.decide` en la convocatoria de la candidatura | 201 · 403 · 404 · 409 (la preselección ya terminó, o no se cumple el umbral) · 422 |
| `GET /api/v1/applications/{id}/preselection-decisions` | `preselection.read` | Historial de decisiones |
| `GET /api/v1/calls/{id}/silence-review` | `preselection.read` | Candidaturas que esperan revisión de silencio (código, etapa y recuentos; sin nombre ni correo) |
| `GET /api/v1/calls/{id}/preselection-policy` | `preselection.read` | Política de la convocatoria |
| `PUT /api/v1/calls/{id}/preselection-policy` | `calls.configure` (solo administración) | Edita días e intentos; se audita el valor anterior y el nuevo |

Cambio aditivo en `POST /applications/{id}/events`: campo opcional `resultado`, solo válido con `tipo = contacto`.

### Decisiones de la PO (Elizabeth, 19/11/2026) / PO decisions

Sustituyen la lista anterior de «interpretaciones que conviene confirmar». / They replace the former list of interpretations to confirm.

| # | Tema | Decisión PO 19/11 | Implementado |
|---|---|---|---|
| 1 | Umbral de silencio | **Dos niveles, editables por convocatoria.** Alerta **leve** desde 2 intentos `sin_respuesta` (sin esperar días). Alerta de **acción** con 4 intentos y 30 días desde el último. Solo la de acción permite confirmar el silencio. Una respuesta o una reprogramación reinicia la cuenta; un intento sin resultado no cuenta | Sí: `call.silence_warning_contacts` (1 ≤ leve ≤ acción), `evidence.alert_level` (`leve`/`accion`), `silence-review` lista ambos niveles |
| 2 | Reprogramar | Reinicia la cuenta y mantiene la etapa. Se puede reprogramar con alerta leve o de acción; sin alerta, error explicado | Sí |
| 3 | Errores | **Mensajes para personas no técnicas**, no «409» | Sí en este módulo: `detail` explica qué pasa y qué hacer; `code` estable para la interfaz (`app/core/errors.py`). Anas muestra el mensaje |
| 4 | Etapa tras confirmar silencio | `retirada`, distinguida por la decisión y la evidencia | Sin cambios |
| 5 | Retirada expresa | Disponible **siempre durante preselección y selección** (`enviada`, `requisitos_en_revision`, `convocada`, `evaluacion_en_curso`, `pendiente_decision_humana`). Tras la admisión, el abandono es una **baja de matrícula** | Sí: retirada en selección. La baja de matrícula es otra entidad (`Enrollment`) y queda **fuera de esta PR**; aquí la API responde con un mensaje que lo indica |
| 6 | Quién edita la política | **Administración y captación** (captación dentro de su programa) | Sí: permiso `preselection.configure` |
| 7 | Docente | Solo convocatorias que alimentan su cohorte; **administración puede ampliarlo** | Regla sin cambios. Hoy administración amplía el ámbito con asignaciones de rol (`role_assignment`) por cohorte o convocatoria; no existe aún una pantalla o endpoint de invitación de personal |
| 8 | Alertas | La lista **identifica a la persona por su nombre**; el correo solo se ve en el expediente | Sí: `display_name` en `silence-review` |

## ES — Datos y migración

Migración `0005` (aditiva y reversible; encadenada tras `0006` de KAN-135, que a su vez depende de `0004`; una sola cabeza Alembic; `0002`, de F2, no existe): añade `call.silence_days`, `call.silence_max_contacts`, `application_event.resultado` y la tabla `preselection_decision`, con restricciones CHECK. No toca tablas de RAG ni de requisitos.

## ES — Evidencia

Entorno: Linux, Python 3.12, PostgreSQL 16.2 + pgvector local y desechable, datos sintéticos. **VERIFIED en local; el CI del PR no se ha consultado todavía.**

| Comprobación | Resultado |
|---|---|
| `pytest` completo (con #40) | 297 passed, 3 xfailed |
| Pruebas nuevas `test_preselection_closure.py` | 93 |
| Pruebas de mutación manual (quitar control de ámbito, quitar umbral, contar intentos sin resultado, quitar la guarda de etapa) | Los 4 mutantes hacen fallar la suite |
| `alembic upgrade head` / `alembic check` / `downgrade base` / `upgrade head` en base vacía | head `0005`, «No new upgrade operations detected», ciclo correcto |
| `ruff check . --select E4,E7,E9,F` | Sin errores |
| Contrato `contracts/openapi.json` y cliente `schema.gen.ts` | Regenerados (solo adiciones) |

### Actualización 19/11/2026 tras integrar `dev` / Update after merging `dev`

- Revisión de silencio: contactos y decisiones se agrupan una vez por `application_id` (`defaultdict(list)`); coste lineal en lugar de recorrer todos los registros por cada candidatura. Mismas reglas y mismo control de acceso. Pruebas nuevas: varias candidaturas con evidencias separadas y una guarda que falla si las listas se recorren más de una vez. / Silence review groups contacts and decisions once per application (linear instead of quadratic); same rules and access control; new regression tests.
- Cadena `0004 → 0006 → 0005`, `alembic heads` = `0005` (una cabeza); la prueba de downgrade baja a `0006` y comprueba que `call_requirement` se conserva. / Single head; downgrade test goes to `0006` and keeps `call_requirement`.
- Conflictos con KAN-135/KAN-148 resueltos (`models.py`, `main.py` con `prefilter_router` y `preselection_router`); contrato y cliente regenerados. `EXPECTED_CALL_COLUMNS` y el diccionario incluyen `silence_days` y `silence_max_contacts`. / Conflicts resolved, contract and client regenerated, drift test and dictionary updated.
- Evidencia local (PostgreSQL 16 + pgvector desechable, datos sintéticos): `pytest` 427 passed; `alembic upgrade head && alembic check && alembic downgrade base` OK; `ruff` OK; `tsc`, `pnpm test` (48), `pnpm build` y `pnpm gen:api` sin diferencias OK. / Local evidence as listed.

**NOT_RUN:** Docker/Compose, E2E de navegador, typecheck y tests web (no hay cambios de código web; el cliente regenerado solo añade tipos), despliegue.

## ES — Pendiente

- Interfaz (Anas): pantalla de alertas de silencio, formulario de resultado del contacto y botones de convocar / retirada / silencio. El contrato ya está disponible.
- Recordatorios o avisos automáticos de la alerta (Yohanna): pueden consumir `silence-review`; no se ha implementado ninguno.
- Actualizar la matriz RBAC (KAN-90, PR #38) con las rutas y permisos nuevos cuando se fusionen #38 y este PR.
- Baja de matrícula de una persona admitida (decisión PO 19/11): historia aparte sobre `Enrollment`.
- Pendiente de la PO: si la retirada también debe poder registrarse desde `lista_espera` (no se decidió; hoy no se permite).
- Validación de Melissa de lo que la PO decida atribuir al AS-IS.
- Sin límite de envíos ni de intentos de decisión (rate limiting): no es parte de esta tarea.

## EN — What it implements

It implements the PO's TO-BE decisions recorded on 2026-11-18 in KAN-119 and KAN-153. **These are product design decisions, not a process validated by Melissa nor a confirmed AS-IS practice.**

- **Call to selection** ends pre-selection even with requirements still under review (`convocada` from `enviada` or `requisitos_en_revision`); the number of unresolved requirement reviews is stored as evidence.
- **Express withdrawal** (`retirada_expresa`) moves the application to `retirada` with actor, date and reason.
- **Silence** uses a per-call policy (default 30 days and 4 contact attempts, editable). It never closes anything by itself: `GET /calls/{id}/silence-review` computes, on read, which applications reached the threshold. A person then confirms the closure (`silencio_confirmado`) or postpones it (`silencio_reprogramado`).
- **Who:** `preselection.read` / `preselection.decide` for admin, captación, selección, coordinación and docente, checked on the server per call (a teacher through the cohorts the call feeds). Applicant and coder accounts get 403. Only admin edits the policy (`calls.configure`).
- **Audit:** every decision writes an immutable `preselection_decision` row (actor, date, reason, from/to stage, evidence snapshot with the thresholds used, so later policy edits never rewrite history), a CRM event, and an audit event with IDs and codes only (never the free-text reason). Each contact attempt now records channel, date and **result** (`respondida` / `sin_respuesta`).

Superseded by the PO decisions of 19/11/2026 (table above): two alert levels (light from 2 unanswered attempts, action at 4 attempts and 30 days, all per call), plain-language errors with stable codes, withdrawal during pre-selection and selection (after admission it is an enrollment withdrawal, out of this PR), policy edited by admin and captación, teacher scope extendable by admin, and alerts showing the person's name. Former interpretations: (1) threshold = at least *N* unanswered attempts since the last answer or postponement **and** at least *D* days since the last of them; an attempt without a recorded result never counts; (2) postponing restarts the count and keeps the stage; (3) confirming silence requires the threshold (otherwise 409; use express withdrawal if the person said so); (4) a confirmed silence also ends in stage `retirada`, distinguished by decision and evidence — a dedicated stage would change the contract vocabulary and is left to the KAN-119 state machine; (5) express withdrawal is limited to pre-selection stages here; (6) only admin edits the policy; (7) teachers reach only calls that feed their cohort; (8) the alert list shows no name or email.

Migration `0005` is additive and reversible and chains after `0006` (KAN-135, which revises `0004`), keeping a single Alembic head (`0002`, F2, does not exist). Evidence: local disposable PostgreSQL 16, synthetic data: 297 passed / 3 xfailed (93 new tests), all four manual mutants caught, `alembic check` clean, upgrade/downgrade cycle OK, CI-rules ruff clean, contract and client regenerated (additions only). **Not run:** Docker/Compose, browser E2E, web typecheck/tests, deployment, and the PR's CI at the time of writing.

Pending: UI (Anas), alert reminders (Yohanna), RBAC matrix update (KAN-90/#38), PO decisions above, Melissa's validation of whatever the PO attributes to the AS-IS, rate limiting.
