# KAN-124 — Registration validation / Validación de inscripción

Owner / responsable: Yohanna. Reviewer / revisión: Anas (`Anasfady`), backend interpretation / contrato backend: Elizabeth.
Jira deadline / vencimiento: 01/12/2026 (description has proposed 19/11 / descripción con propuesta 19/11).

## ES

Actualización 18/11: rama integrada con `dev` `019ab38515f49b2f640df6ebaec09939a203293b`, incluido #23. Tres casos strict-xfail cubren `nombre`, `motivacion` y `EventCreate.resumen`. Quien corrija los validadores debe retirar las tres marcas en el mismo cambio y comprobar rechazo sin escrituras parciales. La decisión de rechazar extras sigue fuera de este PR.

Incremento de pruebas API F1, no una modificación de formulario/contrato ni una certificación del navegador. La cobertura anterior ya prueba consentimiento falso, correo inválido, motivación corta, convocatoria cerrada/inexistente, duplicado normalizado e inscripciones concurrentes. No se repiten sin añadir garantías.

El nuevo `api/tests/test_registration_validation.py` prueba: límites mínimos/máximos y valores fuera de rango, campos obligatorios ausentes, disponibilidad válida, rechazos sin personas/candidaturas/eventos/auditorías parciales ni consumo de códigos, conservación de la identidad original ante duplicado y rechazo efectivo de atributos de autoridad enviados como extras al formulario público. El contrato actual ignora extras: el test verifica que no imponen etapa, rol, persona o autor; no afirma rechazo HTTP 422 de esos extras.

Usa las fixtures PostgreSQL sintéticas existentes, que migran y vacían tablas. Ejecutar **solo contra BD local desechable dedicada**, nunca compartida o producción. Desde `api/` con dependencias y `GISTAR_TEST_DATABASE_URL` configuradas:

```sh
python -m pytest tests/test_registration_validation.py -q
```

CI API lo descubre con su `pytest` normal. Validación local: sintaxis y diff; no se ejecutó PostgreSQL/pytest local por falta de acceso Docker. La ejecución real se informa en Checks del PR. Permisos detallados y navegador siguen en PR #17/#19; este archivo complementa esas pruebas.

Limitación conocida fuera de este cambio: `nombre`/`motivacion` aplican longitud antes del recorte; un texto de espacios puede pasar la primera validación y quedar vacío. Dos casos `xfail(strict=True)` exigen HTTP 422 como comportamiento deseado y mantienen visible el fallo; cuando el backend lo corrija, XPASS hará fallar la suite hasta retirar la marca. No se cambia el contrato del backend; requiere una corrección única revisada por Elizabeth junto con `EventCreate.resumen` del #18. No se da KAN-124 por terminada solo por este incremento.

## EN

18/11 update: branch merged with `dev` `019ab38515f49b2f640df6ebaec09939a203293b`, including #23. Three strict-xfail cases cover name, motivation and CRM summary. The validator fix must remove all three markers in the same change and verify rejection without partial writes. Rejecting extra fields remains a separate contract decision.

F1 API test increment, not a frontend/contract change or browser certification. Existing tests already cover basic invalid values, duplicates and concurrent registrations. New cases add exact bounds/overflows, missing required fields, valid availability values, rejection atomicity including counters/audit rows, preservation of original identity after duplicate submission and server-derived stage/identity/author despite forged extra input. Extras are currently ignored, so the tests assert no privilege effect rather than HTTP 422 rejection.

Existing fixtures migrate/reset disposable synthetic PostgreSQL. Run the command above only with a dedicated local test database, never shared/production. Existing API CI discovers this file automatically. Local validation covers syntax/diff; local PostgreSQL/pytest was not run because Docker is unavailable. See PR Checks for actual execution. PR #17/#19 retain detailed authorization/browser coverage.

Known follow-up: name/motivation length checks precede trimming. Two `xfail(strict=True)` cases assert the desired HTTP 422 contract; once fixed, XPASS fails the suite until the marker is removed. Elizabeth should review one backend correction covering these fields and #18's `EventCreate.resumen`. This change neither blesses that gap nor silently fixes another owner's contract; the ticket still needs cross-review and any remaining criteria before closure. No Jira, schema, seed, permission or dependency changes.
