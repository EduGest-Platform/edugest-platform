# KAN-124 — Registration validation / Validación de inscripción

Owner / responsable: Yohanna. Reviewer / revisión: Anas (`Anasfady`), backend interpretation / contrato backend: Elizabeth.
Jira deadline / vencimiento: 01/12/2026 (description has proposed 19/11 / descripción con propuesta 19/11).

## ES

Incremento de pruebas API F1, no una modificación de formulario/contrato ni una certificación del navegador. La cobertura anterior ya prueba consentimiento falso, correo inválido, motivación corta, convocatoria cerrada/inexistente, duplicado normalizado e inscripciones concurrentes. No se repiten sin añadir garantías.

El nuevo `api/tests/test_registration_validation.py` prueba: límites mínimos/máximos y valores fuera de rango, campos obligatorios ausentes, disponibilidad válida, rechazos sin personas/candidaturas/eventos/auditorías parciales ni consumo de códigos, conservación de la identidad original ante duplicado y rechazo efectivo de atributos de autoridad enviados como extras al formulario público. El contrato actual ignora extras: el test verifica que no imponen etapa, rol, persona o autor; no afirma rechazo HTTP 422 de esos extras.

Usa las fixtures PostgreSQL sintéticas existentes, que migran y vacían tablas. Ejecutar **solo contra BD local desechable dedicada**, nunca compartida o producción. Desde `api/` con dependencias y `GISTAR_TEST_DATABASE_URL` configuradas:

```sh
python -m pytest tests/test_registration_validation.py -q
```

CI API lo descubre con su `pytest` normal. Validación local: sintaxis y diff; no se ejecutó PostgreSQL/pytest local por falta de acceso Docker. La ejecución real se informa en Checks del PR. Permisos detallados y navegador siguen en PR #17/#19; este archivo complementa esas pruebas.

Limitación conocida fuera de este cambio: `nombre`/`motivacion` aplican longitud antes del recorte; un texto de espacios puede pasar la primera validación y quedar vacío. No se añade una prueba que trate ese comportamiento como correcto ni se cambia silenciosamente el contrato del backend; requiere corrección revisada por Elizabeth. No se da KAN-124 por terminada solo por este incremento.

## EN

F1 API test increment, not a frontend/contract change or browser certification. Existing tests already cover basic invalid values, duplicates and concurrent registrations. New cases add exact bounds/overflows, missing required fields, valid availability values, rejection atomicity including counters/audit rows, preservation of original identity after duplicate submission and server-derived stage/identity/author despite forged extra input. Extras are currently ignored, so the tests assert no privilege effect rather than HTTP 422 rejection.

Existing fixtures migrate/reset disposable synthetic PostgreSQL. Run the command above only with a dedicated local test database, never shared/production. Existing API CI discovers this file automatically. Local validation covers syntax/diff; local PostgreSQL/pytest was not run because Docker is unavailable. See PR Checks for actual execution. PR #17/#19 retain detailed authorization/browser coverage.

Known follow-up: name/motivation length checks precede trimming, so whitespace-only input needs a backend contract correction reviewed by Elizabeth. This change neither blesses that gap nor silently fixes another owner's contract; the ticket still needs cross-review and any remaining criteria before closure. No Jira, schema, seed, permission or dependency changes.
