# KAN-145 — Server requirement review in the dossier / Requisitos reales en ficha

## ES

Sobre dev `5ca5194`. Conecta la ficha de personal en modo API con GET del catálogo de requisitos de la convocatoria y GET de revisiones de la candidatura, mediante el cliente generado existente. No mezcla ejemplos locales ni inventa revisiones cuando falta un dato. Error/403 y carga son estados separados; no se convierten en «sin revisar».

Una única versión configurada por código es inequívoca. Con varias versiones se exige elegir explícitamente cuál consultar; no se activa latest, no se elige la que cumple, no se persiste la elección ni se ejecuta el prefiltro. Hasta completar las elecciones no se muestra un resumen de cumplimiento. Las revisiones se usan solo si referencia e ID de definición coinciden; motivos/autor de revisiones antiguas sin vínculo verificable no se presentan como evidencia válida. Se avisa de esas revisiones. El resumen describe únicamente las versiones mostradas, no elegibilidad ni admisión.

Mantiene estados requerido/recomendado y motivos/autor/fecha que la API permite consultar. No copia financiador al panel. Texto representado por React, sin HTML arbitrario. Consulta de solo lectura, sin roles nuevos, escritura de revisiones ni decisiones. Abort/cancelación y clave por candidatura impiden que respuestas tardías sustituyan el panel de otro expediente. Actualizar vuelve a consultar y reinicia la selección de versiones.

Anas conserva la responsabilidad de Jira; preparado por Yohanna con autorización para avanzar trabajo del equipo. Revisión: Elizabeth principal para contrato/permisos y Anas para integración UX. No se modifica Jira ni se certifica aceptación completa de la historia.

## EN

Replaces the API dossier's unavailable placeholder with real call-catalogue and application-review reads. Loading, denied/failed reads and missing reviews remain distinct; there is no local-fixture fallback. Review evidence requires matching reference AND definition ID. Unbound/unknown reviews are flagged, never accepted as met.

One configured version is unambiguous; multiple versions require an explicit display choice for every logical code before a summary appears. No latest-version activation, favorable-version auto-selection, stored policy change, prefilter execution or admission decision. The summary is scoped to displayed versions. Refresh reloads both sources and clears choices. Scope keys, cancellation and stale-response guards isolate dossiers. No new API/schema/permissions/dependencies or production writes.

## Validation / Validación

Local TypeScript, 63 unit tests, production build, E2E script syntax and diff checks PASS. Projection regressions cover all five states, empty/missing data, legacy/wrong-definition binding, explicit multiple versions, required/recommended meaning and deterministic grouping. Browser registration journey extended with two real catalogue versions, a persisted negative review, explicit selection, version isolation and refreshed amendment. Real browser/PostgreSQL E2E is NOT RUN locally (services unavailable); current-head CI supplies that evidence. No real learner data or savings claim.
