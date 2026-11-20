# KAN-129 — Synthetic references and stable errors / Referencias sintéticas y errores estables

## Dates / Fechas

KAN-129 deadline **20/11/2026 — today / hoy**. Parent KAN-53 deadline **19/11/2026 — overdue / vencida**. Prepared on 20/11 from dev `310f766`. Dates are Jira deadlines, not changed commitments or completion claims. Owner Yohanna; David primary reviewer, Elizabeth secondary.

## ES

Seguimiento de los dos comentarios no bloqueantes de la revisión del #57. Las nuevas peticiones de simulación exigen `synthetic-` seguido de una etiqueta técnica en minúsculas, con letras/dígitos y segmentos separados por guion, longitud total 11–80. Se rechazan números de teléfono o documentos sin prefijo; también se filtran formas reconocidas tras el prefijo, incluidas separaciones por guion y secuencias largas de siete o más dígitos. Se reutiliza el detector `find_personal_data` existente, sin consultar nombres de personas ni añadir dependencias.

Esto reduce entradas personales accidentales, pero no es un detector semántico de todos los nombres/datos personales. No usar identificadores reales disfrazados con el prefijo. Los ejemplos técnicos válidos conservan su significado: se recortan espacios externos como antes, el hash/idempotencia y la versión de regla no cambian. Un reintento de referencia válida mantiene el ID original.

El 409 fuera de preselección usa `UserFacingError`, código estable `simulation_outside_preselection`, mensaje que explica qué hacer y el request_id habitual. No se cambian permisos, etapas permitidas ni reglas de disparo. Tests cubren las siete etapas fuera de preselección y comprueban ausencia de escrituras.

**Compatibilidad:** es un endurecimiento deliberado de la entrada. Clientes que envíen referencias antiguas no sintéticas recibirán 422 y deben adoptar referencias técnicas de prueba. No se renombran ni borran registros existentes; el historial conserva su contrato de salida tolerante y permite consultar referencias antiguas. Esto no limpia ni certifica privacidad de datos históricos. Sin migración ni operación sobre BD compartida.

## EN

Follow-up to #57's non-blocking review points. New requests require lowercase synthetic technical references, total length 11–80, with hyphen-separated segments. Existing personal-data detection plus long numeric-run rejection blocks bare/prefixed/separated phone/document shapes. No database name lookup, new dependency or comprehensive PII-detection claim. Historical rows are neither rewritten nor deleted; their output field stays unrestricted for compatibility.

Outside-preselection conflicts now use the existing user-facing error contract, with stable `simulation_outside_preselection`, actionable Spanish detail and standard request correlation. Valid-reference normalization, scheduling, hashing, retry semantics, rule version, permissions and business state are unchanged. Legacy/non-synthetic inputs now fail 422 deliberately; clients must adopt technical synthetic IDs for new simulations.

## Validation / Validación

Local ruff, compilation, request-schema smoke, 45 automation unit tests, OpenAPI/TypeScript generation, typecheck and diff checks PASS. PostgreSQL/Docker NOT RUN locally; current-head CI is the DB evidence source. Added regressions cover 14 invalid reference forms with sanitized validation responses, four valid/normalized/boundary forms and stable retries, seven 409 stages without writes, and readable legacy history with rejected legacy creation. Existing concurrency/rollback/scope/migration tests remain active. No Jira mutation, deployment or completion claim.
