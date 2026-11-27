# KAN-175 · Privacidad del motivo interno / Internal reason privacy

Fecha / Date: 2026-11-27. Base: `dev@746f386`. Datos sintéticos / Synthetic data only.

## Alcance / Scope

**ES** — Decisión de PO del 22/11: la comunicación externa de no admisión es genérica y el motivo individual solo lo ve el personal autorizado. Este cambio añade `api/tests/test_selection_reason_privacy.py`. No cambia el código de la aplicación, el esquema ni el contrato.

**EN** — PO decision of 22/11: external non-admission communication is generic and the individual reason is visible to authorised staff only. This change adds `api/tests/test_selection_reason_privacy.py`. No application code, schema or contract change.

## Qué comprueba / What it checks

| Canal / Channel | Comprobación / Check |
|---|---|
| `GET /me/applications`, `.../selection-outcome` | Sin motivo con voto pendiente y tras la decisión / No reason while a vote is pending or after the decision |
| `GET .../selection-decisions` | El personal de selección lee ambos motivos. 403: solicitante, captación, docencia y selección de otra convocatoria. 401: sin sesión / Selection staff read both reasons. 403: applicant, recruitment, teacher, selection staff of another call. 401: no session |
| `GET /applications/{id}` | 403 al solicitante; la ficha que abre captación no lleva el motivo / 403 for the applicant; the dossier recruitment opens has no reason |
| `POST .../selection-decisions` rechazado / rejected | 403, 409 y 422 no devuelven el motivo enviado / 403, 409 and 422 do not echo it |
| Historial CRM y auditoría / CRM history and audit trail | Sin motivo / No reason |
| Logs de la aplicación / Application logs | Sin motivo; exige haber capturado el log de acceso / No reason; requires the access log to have been captured |

Quórum por defecto: dos personas / Default quorum: two people.

## Evidencia / Evidence

**ES** — PostgreSQL 16.15 con pgvector, desechable y local. Python 3.13.15 (el CI usa 3.12). Desde `api/`:

**EN** — Disposable local PostgreSQL 16.15 with pgvector. Python 3.13.15 (CI uses 3.12). From `api/`:

- `pytest` on every test file that mentions a selection endpoint or model, plus `test_applications.py`, `test_rbac_matrix.py` and `test_contract.py`: **370 passed**.
- `tests/test_final_quorum_transaction.py` and `tests/test_waitlist_last_place.py` (part of the 370, also run by name): **3 passed**.
- `ruff check . --select E4,E7,E9,F`: passed. `alembic heads`: `0024_merge_heads`. `alembic check`: no new operations.

**Comprobación de que la prueba detecta fugas / Proof that the test detects leaks.** Cada fuga se inyectó por separado y después se restauró el código; la prueba falló en las seis. / Each leak was injected on its own and then reverted; the test failed in all six:

1. Reason as the CRM text of the final decision.
2. Reason as the CRM text of a pending vote.
3. Reason in the audit metadata.
4. Reason written to an application log line.
5. `selection.read` granted to recruitment.
6. 422 response echoing the submitted input.

Las fugas 1–5 se repitieron con la versión final; la 6 se probó solo con ella. / Leaks 1–5 were repeated against the final version; leak 6 was only run against it.

## No cubierto y decisiones abiertas / Not covered and open decisions

**ES**

- No se envían correos (KAN-50): habrá que probar ese canal cuando exista.
- No se revisan los logs del servidor PostgreSQL ni los de procesos externos.
- La prueba no consulta el resumen de selección, la bandeja de captación, los agregados, el asistente ni el endpoint de auditoría. La revisión estática no encontró lecturas del motivo en la bandeja, los agregados ni el asistente.
- La decisión del 22/11 menciona **roles autorizados configurables por convocatoria**. Hoy solo es configurable el quórum; los roles con `selection.decide` están fijos en `api/app/core/authz.py`.
- El título del ticket menciona una **recomendación externa de no admisión**. No existe un campo ni un mensaje específico: la persona solicitante recibe etapa, resultado y fecha. Falta que la PO confirme si eso basta.

**EN**

- No e-mail is sent (KAN-50): that channel needs its own test once it exists.
- PostgreSQL server logs and external process logs are not inspected.
- The test does not query the selection overview, recruitment inbox, aggregates, assistant or audit endpoint. Static review found no read of the reason in the inbox, aggregates or assistant.
- The 22/11 decision mentions **authorised roles configurable per call**. Only the quorum is configurable today; the roles holding `selection.decide` are fixed in `api/app/core/authz.py`.
- The ticket title mentions an **external non-admission recommendation**. There is no specific field or message: the applicant receives stage, outcome and date. The PO still needs to confirm whether that is enough.
