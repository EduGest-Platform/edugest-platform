# KAN-120 — CRM events and minimal notes / Eventos CRM y notas mínimas

Owner / responsable: Yohanna. Reviewer / revisión: Elizabeth. Prepared / fecha: 2026-11-17.
Scope / alcance: definition deliverable for KAN-120, not KAN-127 persistence or F2 handoff implementation / definición, no implementación de persistencia ni traspaso F2.

## ES — contrato actual comprobado

Inspección de `api/app/modules/admissions/{models,schemas,router}.py` y `api/app/core/audit.py` en la base de esta rama. **CODE_PRESENT_NOT_RUN**: se documenta código, no se certifica un recorrido ejecutado.

| Evento | Entrada pública de personal autorizado | Significado y límite |
|---|---|---|
| `contacto` | Sí | Registro de una interacción ya ocurrida; no prueba envío automático. Canal opcional entre email, telefono, presencial, videollamada. |
| `nota` | Sí | Contexto operativo mínimo del expediente. No sustituye una decisión ni almacena información sensible. |
| `recordatorio` | Sí | Registro CRM de un recordatorio; no demuestra correo entregado, ejecución del motor ni ahorro de tiempo. |
| `creada` | No | Evento interno al crear/importar candidatura; no se acepta en `EventCreate`. |
| `cambio_etapa` | No | Existe en el vocabulario del modelo, pero el endpoint CRM no lo admite. Cambio de etapa reservado a flujos humanos autorizados. |

`POST /api/v1/applications/{application_id}/events` requiere permiso `applications.crm` y ámbito del expediente. El servidor impone autor y fecha; no confiar en un actor remitido en el body. El texto `resumen` se limita a 1–500 caracteres por esquema y se recorta al escribir. **Limitación actual:** un texto solo de espacios puede superar la validación previa al recorte; corregirlo requiere un PR de contrato/validación del backend, no se presenta como resuelto aquí.

Captación/selección pueden registrar según su ámbito; administración dispone de permiso global. La vista propia de persona no expone historial CRM. Este documento describe la política actual F1: no autoriza nuevos roles ni presume que coordinación tenga acceso nominal. La auditoría `application.event_added` guarda identificador, código y tipo; no copia texto libre. La lectura de expediente registra `application.viewed`.

## ES — política propuesta de contenido mínimo

- Registrar finalidad operativa, resultado breve y acción siguiente en lenguaje objetivo: «Contacto sintético: confirma asistencia; pendiente de revisar documentación». No copiar mensajes completos ni documentos.
- No introducir salud/discapacidad, situación familiar/económica, origen, contraseñas, tokens, correos/teléfonos adicionales ni valoraciones personales en notas. Referir únicamente el estado de revisión documental cuando corresponda.
- No afirmar «enviado», «admitida», «descartada» o «cerrada por silencio» por crear un evento. Los estados sensibles requieren el flujo autorizado y confirmación humana; silencio significa pendiente de revisión.
- El canal del contacto no equivale a `canal_origen` de la candidatura. Fecha/actor del evento describen el registro, no un sistema de citaciones completo.
- No exportar notas a logs, métricas del 70 % ni prompts de IA. El evento CRM no es una evidencia de automatización: harían falta registros de ejecución únicos, tarea, versión, resultado y auditoría verificables.
- No fijar un plazo de retención inventado. Elizabeth debe aprobar retención, corrección/borrado, acceso histórico y campos estructurados de resultado/próxima acción antes de ampliar modelos (KAN-127/KAN-144).

## EN — current contract and proposed content policy

The inspected F1 code accepts staff `contacto`, `nota` and `recordatorio` events; channels are email/telefono/presencial/videollamada. Internal `creada` and `cambio_etapa` are not accepted by EventCreate. The endpoint enforces application role/scope and derives author/time server-side. `resumen` is schema-limited to 1–500 characters then stripped. Whitespace-only input is a known validation gap, not fixed by this documentation change.

Authorized captación/selección are scope-bound; admin has global permission. Own-application views omit internal CRM history. Coordination does not gain nominal access through this document. Success audit contains identifiers/code/type, never note text; dossier reads are audited separately. Code inspection is **CODE_PRESENT_NOT_RUN**, not runtime certification.

Proposed notes contain only operational purpose, concise objective result and next action. Do not copy raw messages, documents, health/disability, family/financial circumstances, origin, credentials, extra contacts or subjective assessments. Record document-review status only. A CRM reminder is not proof of delivered mail, automated execution or time saved; creating a note never decides admission/exclusion or closes silence cases. Contact channel and application origin are distinct.

Do not export notes into logs, time-saved evidence or model prompts. Execution evidence needs separate unique task/version/result/audit records. Retention, historical access, correction/deletion and structured next-action/result fields require Elizabeth's approval before KAN-127/KAN-144 integration. No retention period, new field or permission is invented here.

## Review checklist / Lista de revisión

- [ ] Elizabeth approves event meanings/content minimization / aprueba significado y minimización.
- [ ] Confirm retention and historical access owner / confirmar retención y acceso histórico.
- [ ] Decide structured result/next-action fields and whitespace validation follow-up / decidir campos y validación de espacios.
- [ ] Cross-review before closing KAN-120 / revisión antes de cerrar.

No API, migration, seed, Jira or deployment changes / sin cambios de API, migraciones, seed, Jira o despliegue.
