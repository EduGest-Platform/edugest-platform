# KAN-153 — End of pre-selection with audit / Fin de preselección con auditoría

Owner / responsable: Elizabeth. Reviewer / revisión: Yohanna. Prepared / fecha: 2026-11-18.
Status / estado: **implemented and tested locally; not merged** / implementado y probado en local; sin fusionar. Stacked on PR #40 (KAN-128) because both use migration chain 0004 → 0005 and the same scope check / apilada sobre #40 por la cadena de migraciones y el mismo control de ámbito.

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

### Interpretaciones que conviene confirmar (no están en las decisiones de la PO)

1. **Cuándo se cumple el umbral de silencio:** hay al menos *N* intentos de contacto con resultado `sin_respuesta` desde la última respuesta o reprogramación **y** han pasado al menos *D* días desde el último de esos intentos. Un intento sin resultado registrado **no cuenta** (nunca se empuja hacia el cierre sin evidencia). Una respuesta registrada reinicia la cuenta.
2. **Reprogramar** reinicia la cuenta: harán falta otros *N* intentos sin respuesta y *D* días. Deja la etapa como está y añade una nota al CRM.
3. **Confirmar el silencio** exige que el umbral se cumpla; si no, 409. Quien tenga constancia de que la persona desiste debe usar `retirada_expresa`.
4. **Etapa tras confirmar silencio:** `retirada`, igual que la retirada expresa. Se distinguen por la decisión (`silencio_confirmado` frente a `retirada_expresa`) y por la evidencia, no por una etapa nueva (añadirla cambia el vocabulario del contrato y de la interfaz). Consecuencia: los agregados de coordinación por etapa las suman. **Decisión pendiente de la PO** (propuesta: etapa propia en la máquina de estados de KAN-119).
5. **Retirada expresa solo desde la preselección** (`enviada`, `requisitos_en_revision`). KAN-119 propone «cualquier estado abierto»; los estados posteriores quedan para la máquina de estados completa.
6. **Quién edita la política:** solo administración. La PO dijo que es editable por convocatoria, pero no quién la edita.
7. **Docente:** su ámbito es la cohorte; solo alcanza candidaturas de convocatorias que alimentan esa cohorte (misma regla que KAN-128). Una convocatoria abierta sin cohorte no le da acceso.
8. **Visibilidad para coordinación y docente:** la lista de alertas no muestra nombre ni correo. El historial muestra el motivo, que es texto libre operativo (política de KAN-120: sin datos de salud ni situación personal).

## ES — Datos y migración

Migración `0005` (aditiva y reversible; encadenada tras `0004` porque `0002`, de F2, no existe): añade `call.silence_days`, `call.silence_max_contacts`, `application_event.resultado` y la tabla `preselection_decision`, con restricciones CHECK. No toca tablas de RAG ni de requisitos.

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

**NOT_RUN:** Docker/Compose, E2E de navegador, typecheck y tests web (no hay cambios de código web; el cliente regenerado solo añade tipos), despliegue.

## ES — Pendiente

- Interfaz (Anas): pantalla de alertas de silencio, formulario de resultado del contacto y botones de convocar / retirada / silencio. El contrato ya está disponible.
- Recordatorios o avisos automáticos de la alerta (Yohanna): pueden consumir `silence-review`; no se ha implementado ninguno.
- Actualizar la matriz RBAC (KAN-90, PR #38) con las rutas y permisos nuevos cuando se fusionen #38 y este PR.
- Decisiones de la PO de la sección «Interpretaciones», y validación de Melissa de lo que la PO decida atribuir al AS-IS.
- Sin límite de envíos ni de intentos de decisión (rate limiting): no es parte de esta tarea.

## EN — What it implements

It implements the PO's TO-BE decisions recorded on 2026-11-18 in KAN-119 and KAN-153. **These are product design decisions, not a process validated by Melissa nor a confirmed AS-IS practice.**

- **Call to selection** ends pre-selection even with requirements still under review (`convocada` from `enviada` or `requisitos_en_revision`); the number of unresolved requirement reviews is stored as evidence.
- **Express withdrawal** (`retirada_expresa`) moves the application to `retirada` with actor, date and reason.
- **Silence** uses a per-call policy (default 30 days and 4 contact attempts, editable). It never closes anything by itself: `GET /calls/{id}/silence-review` computes, on read, which applications reached the threshold. A person then confirms the closure (`silencio_confirmado`) or postpones it (`silencio_reprogramado`).
- **Who:** `preselection.read` / `preselection.decide` for admin, captación, selección, coordinación and docente, checked on the server per call (a teacher through the cohorts the call feeds). Applicant and coder accounts get 403. Only admin edits the policy (`calls.configure`).
- **Audit:** every decision writes an immutable `preselection_decision` row (actor, date, reason, from/to stage, evidence snapshot with the thresholds used, so later policy edits never rewrite history), a CRM event, and an audit event with IDs and codes only (never the free-text reason). Each contact attempt now records channel, date and **result** (`respondida` / `sin_respuesta`).

Interpretations to confirm (not in the PO decisions): (1) threshold = at least *N* unanswered attempts since the last answer or postponement **and** at least *D* days since the last of them; an attempt without a recorded result never counts; (2) postponing restarts the count and keeps the stage; (3) confirming silence requires the threshold (otherwise 409; use express withdrawal if the person said so); (4) a confirmed silence also ends in stage `retirada`, distinguished by decision and evidence — a dedicated stage would change the contract vocabulary and is left to the KAN-119 state machine; (5) express withdrawal is limited to pre-selection stages here; (6) only admin edits the policy; (7) teachers reach only calls that feed their cohort; (8) the alert list shows no name or email.

Migration `0005` is additive and reversible and chains after `0004` (`0002`, F2, does not exist). Evidence: local disposable PostgreSQL 16, synthetic data: 297 passed / 3 xfailed (93 new tests), all four manual mutants caught, `alembic check` clean, upgrade/downgrade cycle OK, CI-rules ruff clean, contract and client regenerated (additions only). **Not run:** Docker/Compose, browser E2E, web typecheck/tests, deployment, and the PR's CI at the time of writing.

Pending: UI (Anas), alert reminders (Yohanna), RBAC matrix update (KAN-90/#38), PO decisions above, Melissa's validation of whatever the PO attributes to the AS-IS, rate limiting.
