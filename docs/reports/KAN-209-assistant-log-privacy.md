# KAN-209 — Assistant log privacy / Privacidad de logs del asistente

## ES

Yohanna; revisión solicitada solo a Anas. Deadline **01/12/2026**, base `dev@f4888cc` (24/11). Complementa el inventario de retención existente con pruebas del endpoint documental recién integrado.

Cinco casos verifican respuesta, abstención, 403, validación 422 y fallo de recuperación 500. Se comprueba que el access log capturado exista y lleve el request_id de la respuesta, sin pregunta ni mensaje privado de excepción; la auditoría conserva el resultado sin la pregunta. Los casos 422/500 no simulan una respuesta auditada exitosa. Datos sintéticos, embeddings externos deshabilitados y fecha del corpus fijada. Solo se inyecta el fallo de recuperación del caso 500; no se puentean autenticación ni autorización.

Son controles del proceso API y de su auditoría en estos recorridos: no certifican logs de proxies, proveedor, infraestructura ni políticas de retención/exportación. No se cambian periodos de conservación, permisos ni configuración externa. La revisión de todos los sinks y aceptación de KAN-209 permanecen separadas.

Local: Ruff, compilación Python y diff correctos. Pytest/PostgreSQL no ejecutados localmente; CI no esperado ni declarado correcto, por petición del usuario. No se modifica Jira.

## EN

Owner Yohanna; sole requested reviewer Anas. Deadline **2026-12-01**, `dev@f4888cc` snapshot on November 24.

Five cases extend existing retention inventory to the new document endpoint: answered, no-source, forbidden, validation failure and retrieval exception. Captured access logs must actually contain the correlated request ID, without question/exception text; functional audit must record outcomes without questions. Rejected/failed requests do not fabricate successful assistant audit. Synthetic corpus, fixed date, no external embeddings; only the 500 retrieval failure is injected, not authorization.

This covers API-process logs and functional audit for those paths, not provider/proxy/infrastructure sinks, retention periods or export-policy acceptance. No settings, roles, production data or Jira state changed. Local lint/compilation/diff passed; PostgreSQL tests were not run locally and CI completion is not checked.
