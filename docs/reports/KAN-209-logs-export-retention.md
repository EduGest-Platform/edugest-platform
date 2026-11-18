# KAN-209 — Logs, export and retention / Logs, exportación y retención

**Date / fecha:** 2026-11-18. **Owner / responsable:** Yohanna. **Reviewer / revisión:** Elizabeth.
**Jira deadline / vencimiento:** 01/12/2026. **Inspected base / base:** `dev` `57197c959e2596c53a166f2009312a9bc29fe37f`.
**Status:** static inventory verified / inventario estático comprobado; runtime **CODE_PRESENT_NOT_RUN** in this task; retention decisions **PROPOSED / PENDING**. No compliance or secret-free certification / no certificación de cumplimiento ni ausencia de secretos.

## ES — inventario del estado actual

| Superficie | Evidencia en código | Límite o riesgo a revisar |
|---|---|---|
| Auditoría funcional persistida | `api/app/core/audit.py`, `modules/audit/models.py`: actor ID, roles, acción, tipo/ID destino, metadata, fecha | IDs y roles no equivalen a datos anónimos. `record(**meta)` acepta metadata arbitraria; su docstring pide minimizar, pero no existe un filtro global que lo garantice. |
| Sitios actuales de escritura | Login fallido sin identificador; login/logout, inscripción, lectura de expediente, evento CRM y agregado de convocatoria | Verificar cada nuevo call site. Los metadatos actuales de evento CRM incluyen código/tipo, no el resumen libre; no generalizar esa observación a cualquier futuro módulo. |
| Inmutabilidad de auditoría | Migración `0001_f1_cimientos.py`: trigger por fila antes de UPDATE/DELETE | Impide esos cambios ordinarios, no certifica resistencia frente a administradores/DDL/TRUNCATE ni backup completo. Una purga futura no puede ser un DELETE rutinario sin diseño aprobado. |
| Consulta administrativa | `GET /api/v1/audit-events`: exige `audit.read`; rol admin en F1; filtros por acción/tipo/ID y límite 1–500 | Es consulta JSON, no un sistema completo de exportación. Sin cursor, rango temporal o job de exportación; el límite puede truncar resultados. La consulta de auditoría no se audita a sí misma en el código inspeccionado. |
| Historial CRM | `ApplicationEvent.resumen`, canal, autor, fecha | Contiene texto libre operativo, distinto de auditoría. Su minimización necesita política/revisión; no copiar a logs, métricas o prompts. PR #18 trata la definición de contenido, no se duplica aquí. |
| Logs de proceso | Entrypoint inicia Uvicorn sin desactivar access log; seed imprime estado genérico | No se ha capturado tráfico remoto/local aquí. Revisar rutas/query strings, excepciones y capas de proxy antes de afirmar que todos los logs son seguros. |
| Asistente RAG, previsto DA6 (25/11) | Compromiso de David en revisión del #25, ADR-0005 / #12; no implementado ni ejecutado por este documento | Preguntas libres no deben persistirse en logs ni auditoría. Auditoría propuesta: ruta documentos/datos, IDs de documentos y resultado (respondido/sin fuente/denegado por ámbito). Gemini/Groq reciben preguntas: solo datos sintéticos; verificar implementación, envío y sinks en DA6. |
| Logs de CI/Compose | `.github/workflows/ci.yml` imprime logs Compose al fallar; contraseña de CI se enmascara | Enmascarar variables conocidas no elimina todo dato sensible posible de registros, stack traces o SQL. No subir volcados crudos como evidencia. |
| Sesiones | `expires_at`/`revoked_at` se comprueban al autenticar; TTL configurado | Expiración invalida acceso, no borra filas ni define plazo de conservación. No se encontró purga programada en `api/app/`. |
| Copias y plataforma | Compose conserva volúmenes; Render/Actions tienen configuración externa | Este análisis no inspeccionó cuentas, permisos del workspace, cuotas ni retención del proveedor. No se presupone que expirar una BD sea una política de retención aceptada. |

## ES — frontera con trabajo en paralelo

PR [#23](https://github.com/EduGest-Platform/edugest-platform/pull/23) (KAN-105, Elizabeth) propone request IDs y logs seguros; **abierto al inspeccionar**, no integrado en esta base. Sus pruebas y política se revisan en ese PR con David. No se cambian `core/`, handlers ni contratos desde este documento. Después de fusionarlo, actualizar este inventario y verificar si queda acceso Uvicorn/proxy adicional; no asumir que un logger nuevo elimina los anteriores.

PR [#24](https://github.com/EduGest-Platform/edugest-platform/pull/24) (KAN-107) propone gobernanza de formularios/datos; no sustituir sus decisiones de acceso/minimización ni inventar una política contradictoria. KAN-209 deja pendientes los plazos y operaciones hasta aceptación de Elizabeth y las personas responsables de datos.

## ES — propuesta de manejo y aceptación, aún no implementada

1. **Clasificar antes de conservar:** separar auditoría funcional, acceso/error operativo, notas CRM, sesiones, exports y backups. Para cada conjunto, definir finalidad, responsable, roles lectores, ubicación, plazo aprobado, evento de inicio del plazo, corrección/borrado y evidencia de ejecución. No fijar días arbitrarios.
2. **Minimización verificable:** lista permitida de campos por log/call site; nada de passwords/tokens, Authorization/Cookie, URLs de BD, request bodies o notas. Para correlación, preferir identificador generado por servidor y ruta parametrizada; validar con KAN-105. El ID de auditoría sigue siendo dato de acceso restringido.
3. **Exportación:** confirmar finalidad y destinatario autorizados; preservar ámbito/filtros y total de filas, manifestar truncamiento, evitar texto libre sensible y documentar formato/destino/caducidad. Si se necesita export completo, diseñar paginación/rangos y auditoría de descarga con Elizabeth; el GET limitado actual no lo entrega por sí solo.
4. **Retención y append-only:** no desactivar triggers ni ejecutar purgas para completar esta tarea. Elizabeth debe decidir mecanismo revisable que concilie trazabilidad, política aprobada y eliminación/corrección: migración/archivado o procedimiento privilegiado auditado según diseño. No afirmar que sea una obligación legal concreta ni que append-only autorice conservar indefinidamente.
5. **Evidencia segura:** compartir solo comandos/resultados resumidos, commit, escenario y conteos sintéticos. Si un secreto aparece en logs, no replicarlo en Jira/PR; activar el proceso de respuesta del equipo. Borrar una copia no demuestra retirar logs, artefactos y backups relacionados.

### Comprobaciones pendientes para el cierre

- [ ] Tras #23: pruebas con secretos sintéticos marcadores y query/body/headers, 401/403/422/500, ruta desconocida y proxy; comprobar que todos los sinks omiten valores, no solo un logger.
- [ ] Export/consulta: admin positivo, usuarios fuera de rol/ámbito negativos, filtros/rangos y más de 500 filas sin pérdida silenciosa. No reutilizar un dump sensible como fixture.
- [ ] Política de retención aceptada por conjunto y aplicada a logs de plataforma/Actions además de PostgreSQL.
- [ ] Purga/archivo: autorización, simulación previa, preservación de relaciones, auditoría y prueba en BD sintética desechable; nunca base compartida.
- [ ] Revisión de Elizabeth; actualizar inventario al integrar KAN-105/107 y futuras APIs. Sin aprobación e implementación no dar por cerrada la retención del producto.

## EN — inventory and decisions

The inspected functional audit persists actor/target identifiers, roles, action, timestamp and arbitrary metadata. IDs are not anonymous. Current CRM audit sites use code/type rather than note text, but `record(**meta)` has no universal sanitizing allow-list. Every new caller needs review. The migration's row-level UPDATE/DELETE trigger provides ordinary append-only behavior, not an administrator/DDL/TRUNCATE-proof security guarantee. A future purge needs an explicit approved design.

The admin-only audit GET returns at most 500 JSON rows with action/type/ID filters. It is not a complete export pipeline: no cursor/time range/export job, and reads of the audit endpoint are not themselves audited in the inspected function. CRM free-text history is separate from minimal audit metadata. Uvicorn starts with access logging enabled by omission; CI prints Compose logs on failure and masks known generated passwords. No captured runtime logs were inspected here, so neither all-sink sanitization nor absence of leakage is certified.

Session expiry/revocation invalidates access without deleting records. No scheduled purge was found in the inspected application. Provider/account retention, permissions, volumes and backups were not inspected. Pending PR #23 owns safe error/access-log implementation; #24 owns data-governance design. This document does not overwrite either or treat them as merged. Reconcile the inventory after integration, including any remaining server/proxy access logs.

Proposed acceptance: classify audit/operational logs/CRM/sessions/exports/backups separately; approve purpose, owner, readers, storage, retention trigger/period and correction/deletion mechanism per class. No days or legal determination are invented. Agree minimal fields and test every sink with synthetic secret markers across headers/query/body/errors. Prefer server correlation IDs and parameterized routes. Restricted IDs must still be protected.

Any full export needs authorized purpose/recipient, scoped filters, completeness/truncation handling, safe destination/expiry and download audit. The existing limited GET does not provide that. Do not disable triggers or purge shared data: Elizabeth must approve a traceable archival/migration/privileged mechanism that reconciles append-only history and retention policy. Test authorization, relationships, dry-run counts and evidence on disposable synthetic data only. Logs, artifacts and backups need aligned policy; deleting one copy does not prove erasure everywhere. Do not repost leaked secrets in review evidence.

## Evidence / Evidencia

### Follow-up / Seguimiento — 18/11/2026

ES: [David informó pruebas de ejecución](https://github.com/EduGest-Platform/edugest-platform/pull/25) sobre `error_handling.py` del #23 con Uvicorn 0.54 / Starlette 1.7 y datos sintéticos: el access log escribió ruta y query string sin limpiar; una respuesta 500 produjo traceback con mensaje de excepción. Son **dos sinks con exposición observada por el revisor**, no una sospecha estática ni pruebas ejecutadas por Yohanna. Evidencia original: [revisión de #23](https://github.com/EduGest-Platform/edugest-platform/pull/23#pullrequestreview-5953988171). No se reproducen valores ni logs crudos.

EN: [David reported runtime tests](https://github.com/EduGest-Platform/edugest-platform/pull/25) of #23's `error_handling.py` under Uvicorn 0.54 / Starlette 1.7 with synthetic data: the access log emitted raw path/query strings, and a 500 emitted a traceback including the exception message. These are **two sinks observed by the reviewer**, not merely a static concern or tests run by Yohanna. See the [original #23 review](https://github.com/EduGest-Platform/edugest-platform/pull/23#pullrequestreview-5953988171); raw logs/values are not copied here.

ES: La corrección propuesta en #23 combina `--no-access-log` y captura del 500 dentro del middleware. Tras integrarla, repetir los marcadores sintéticos contra ambos sinks y cualquier proxy; hasta entonces la lista de cierre sigue pendiente. Esta evidencia no altera el snapshot del inventario ni certifica el estado de `dev` posterior.

EN: The proposed #23 fix combines `--no-access-log` and catching 500 errors inside middleware. After integration, rerun synthetic markers against both sinks and any proxy; closing checks remain pending. This evidence does not change the inventory snapshot or certify later `dev`.

EN — planned RAG row above: David's DA6 commitment for 25/11 records only route (documents/data), document IDs and outcome (answered/no source/denied by scope) in functional audit, without question text or questions in application logs. Questions go to Gemini/Groq, so synthetic data only. This is a planned contract, not verified implementation; review provider transmission and all sinks in DA6. Retention periods and acceptance remain with Elizabeth/data owners.

Static inspection / inspección: audit helper/model/router, all current `audit.record` callers, auth/deps/config/seed, migration 0001, entrypoint and CI failure logging. Existing `test_crm_audit.py` covers append-only and minimal CRM/login-failure audit, but **was not executed locally for this documentary task**. Source checks and diff validation are recorded in the PR; CI results are separate. No capture/export/purge, provider settings, new endpoint, permissions, Jira or deployment changes.
