# KAN-184 — Staff silence alerts / Alertas de silencio

## ES

Fecha de comprobación: 23/11/2026. Deadline: **20/11/2026 (vencido)**.

La lista de expedientes consulta el endpoint existente `GET /api/v1/calls/{call_id}/silence-review` al seleccionar una convocatoria. Presenta los niveles y umbrales calculados por el servidor, intentos sin respuesta, fecha disponible y acceso al expediente. Los filtros de texto/estado no limitan esta lista: cubre toda la convocatoria seleccionada. El botón de actualización permite consultar evidencia nueva después de un contacto.

No recalcula reglas ni cierra candidaturas. Las respuestas de convocatorias anteriores se cancelan y descartan; los errores de autorización se muestran como errores, nunca como una lista vacía. No envía mensajes ni modifica políticas.

Evidencia local: TypeScript, 67 tests Vitest y compilación Vite correctos; sintaxis del recorrido E2E correcta. El recorrido ampliado crea contactos sintéticos, comprueba aviso, apertura del expediente, etapa intacta, desaparición tras respuesta y denegación para otro programa. Su ejecución requiere PostgreSQL y navegador en CI; no se ejecutó localmente. Revisión: Anas.

## EN

Checked 2026-11-23. Deadline: **2026-11-20 (overdue)**.

Selecting a call loads the existing silence-review endpoint. The call-wide read-only list displays server evidence and configured thresholds, opens the existing dossier and supports manual refresh. It does not apply list search/stage filters, recalculate policy, send messages or close applications. Aborted/stale requests cannot display evidence from another call; authorization failures remain visible errors.

Local TypeScript, 67 Vitest tests, Vite build and E2E syntax checks passed. The extended synthetic browser scenario covers unanswered-contact warnings, dossier navigation, unchanged stage, response-based clearing and foreign-program denial. Database/browser execution is delegated to CI and was not run locally. Reviewer: Anas.
