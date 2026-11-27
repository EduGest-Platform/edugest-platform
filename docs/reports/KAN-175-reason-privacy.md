# KAN-175 · Privacidad del motivo interno / Internal reason privacy

Fecha / Date: 2026-11-27. Base histórica / Historical baseline: `dev@746f386`. Review follow-up base: `dev@da43c2c` (includes #296 and #292). Datos sintéticos / Synthetic data only.

## Alcance / Scope

**ES** — Decisión de PO del 22/11: la comunicación externa de no admisión es genérica y el motivo individual solo lo ve el personal autorizado. Este cambio añade `api/tests/test_selection_reason_privacy.py`. No cambia el código de la aplicación, el esquema ni el contrato.

**EN** — PO decision of 22/11: external non-admission communication is generic and the individual reason is visible to authorised staff only. This change adds `api/tests/test_selection_reason_privacy.py`. No application code, schema or contract change.

## Qué comprueba / What it checks

| Canal / Channel | Comprobación / Check |
|---|---|
| `GET /me/applications`, `.../selection-outcome` | Sin motivo completo o fragmentos; etapa pendiente sin resultado ni fecha; decisión definitiva no admitida con fecha y sin matrícula / No full reason or fragments; pending stage with no outcome or date; final non-admission with date and no enrollment |
| `GET .../selection-decisions` | El personal de selección lee ambos motivos. 403: solicitante, captación, docencia y selección de otra convocatoria antes y después de la decisión definitiva. 401: sin sesión / Selection staff read both reasons. 403: applicant, recruitment, teacher, selection staff of another call before and after the definitive decision. 401: no session |
| `GET /applications/{id}` | 403 al solicitante; la ficha que abre captación no lleva el motivo / 403 for the applicant; the dossier recruitment opens has no reason |
| `POST .../selection-decisions` rechazado / rejected | 403, 409 y 422 no devuelven el motivo enviado; escritura fuera de convocatoria rechazada antes y después de decidir / 403, 409 and 422 do not echo it; out-of-call writes rejected before and after decision |
| Historial CRM y auditoría / CRM history and audit trail | Sin motivo / No reason |
| Logs de la aplicación / Application logs | Sin motivo; exige haber capturado el log de acceso / No reason; requires the access log to have been captured |

Quórum por defecto: dos personas / Default quorum: two people.

## Evidencia histórica / Historical evidence

**ES** — PostgreSQL 16.15 con pgvector, desechable y local. Python 3.13.15 (el CI usa 3.12). Desde `api/`:

**EN** — Disposable local PostgreSQL 16.15 with pgvector. Python 3.13.15 (CI uses 3.12). From `api/`:

- `pytest` sobre todos los archivos de prueba que mencionan un endpoint o modelo de selección, más `test_applications.py`, `test_rbac_matrix.py` y `test_contract.py` / on every test file that mentions a selection endpoint or model, plus those three: **370 passed**.
- `tests/test_final_quorum_transaction.py` y/and `tests/test_waitlist_last_place.py` (incluidos en las 370 y ejecutados también por nombre / part of the 370, also run by name): **3 passed**.
- `ruff check . --select E4,E7,E9,F`: passed. `alembic heads`: `0024_merge_heads`. `alembic check`: no new operations.

**Comprobación de que la prueba detecta fugas / Proof that the test detects leaks.** Cada fuga se inyectó por separado y después se restauró el código; la prueba falló en las seis. / Each leak was injected on its own and then reverted; the test failed in all six:

1. Motivo como texto CRM de la decisión final / Reason as the CRM text of the final decision.
2. Motivo como texto CRM de un voto pendiente / Reason as the CRM text of a pending vote.
3. Motivo en los metadatos de auditoría / Reason in the audit metadata.
4. Motivo escrito en una línea de log de la aplicación / Reason written to an application log line.
5. `selection.read` concedido a captación / granted to recruitment.
6. Respuesta 422 que devuelve la entrada enviada / 422 response echoing the submitted input.

Las fugas 1–5 se repitieron con la versión final; la 6 se probó solo con ella. / Leaks 1–5 were repeated against the final version; leak 6 was only run against it.

## Revisión posterior / Review follow-up

**ES** — Marcadores sintéticos diferenciados por voto; se comprueban todas las ventanas de ocho caracteres alfanuméricos normalizados de cada motivo, con independencia de mayúsculas y separadores. Las pruebas del propio detector simulan fragmentos iniciales, finales, interiores y texto separado. No garantiza detectar fragmentos inferiores a ocho caracteres, traducciones ni todas las transformaciones posibles. Se comprueba el contrato completo del resultado propio y el conjunto de campos permitido de la lista propia. La prueba entre convocatorias exige controles positivos autorizados tanto con voto pendiente como tras la decisión definitiva, y rechaza lecturas y escrituras del selector ajeno en ambos momentos.

**EN** — Distinct synthetic markers per vote; all eight-character normalized alphanumeric windows of each reason are checked, regardless of case and separators. Detector tests simulate initial, final, interior and separated fragments. This does not guarantee detection of fragments shorter than eight characters, translations or all possible transformations. The complete own-outcome contract and the allowed own-list fields are checked. Cross-call tests require authorized positive controls before and after the final decision and reject the out-of-scope selector's reads and writes at both points.

**ES** — La evidencia anterior corresponde a la versión previa. Las nuevas regresiones y el CI sobre la rama actualizada requieren ejecución y revisión independiente; no se presentan como superados aquí.

**EN** — The evidence above applies to the previous version. The new regressions and CI on the updated branch require execution and independent review; no passing result is claimed here.

## No cubierto y decisiones abiertas / Not covered and open decisions

| Endpoint pendiente / Pending endpoint | Cobertura requerida / Required coverage |
|---|---|
| `GET /api/v1/calls/{call_id}/selection-overview` | Roles y ámbitos, antes y después de decidir / Roles and scopes, before and after decision |
| `GET /api/v1/recruitment/inbox`, `GET /api/v1/applications` | Listas y paginación sin motivos / Lists and pagination without reasons |
| `GET /api/v1/calls/{call_id}/summary` | Agregados sin motivos / Aggregates without reasons |
| `GET /api/v1/audit-events` | Respuesta API y permisos, además de las filas de auditoría ya comprobadas / API response and permissions, beyond existing audit-row checks |
| `POST /api/v1/assistant/ask`, `POST /api/v1/assistant/ask/stream` | Consulta autorizada y respuesta no filtrada por error, incluyendo SSE / Authorized retrieval and no accidental disclosure, including SSE |
| Otros endpoints relacionados de candidatura y exportaciones futuras / Other related application endpoints and future exports | Inventariar y probar rutas de lectura, mutación y errores según rol / Inventory and test read, mutation and error paths by role |

**ES**

- No se envían correos (KAN-50): habrá que probar ese canal cuando exista.
- No se revisan los logs del servidor PostgreSQL ni los de procesos externos.
- La prueba no consulta el resumen de selección, la bandeja de captación, los agregados, el asistente ni el endpoint de auditoría. La revisión estática no encontró lecturas del motivo en la bandeja, los agregados ni el asistente.
- La decisión del 22/11 menciona **roles autorizados configurables por convocatoria**. Hoy solo es configurable el quórum; los roles con `selection.decide` están fijos en `api/app/core/authz.py`.
- El título del ticket menciona una **recomendación externa de no admisión**. No existe un campo ni un mensaje específico: la persona solicitante recibe etapa, resultado y fecha. La recomendación externa permanece pendiente en KAN-175; no se considera aceptada ni implementada.

**EN**

- No e-mail is sent (KAN-50): that channel needs its own test once it exists.
- PostgreSQL server logs and external process logs are not inspected.
- The test does not query the selection overview, recruitment inbox, aggregates, assistant or audit endpoint. Static review found no read of the reason in the inbox, aggregates or assistant.
- The 22/11 decision mentions **authorised roles configurable per call**. Only the quorum is configurable today; the roles holding `selection.decide` are fixed in `api/app/core/authz.py`.
- The ticket title mentions an **external non-admission recommendation**. There is no specific field or message: the applicant receives stage, outcome and date. The external recommendation remains open in KAN-175; it is not considered accepted or implemented.
