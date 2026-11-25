# KAN-192 — F2 HTTP admission to enrollment / Inscripción a matrícula por HTTP

## ES

Yohanna; único revisor solicitado: Anas. Deadline Jira **25/11/2026 (mañana respecto al 24/11)**. Base `dev@357cad1`, que ya incluye entregas y quórum. Incremento independiente de los cambios pendientes de #121.

Este recorrido usa fetch contra una API HTTP real en localhost, no TestClient ni mocks de rutas. Comprueba inscripción pública, expediente único, contacto, denegación de otro programa, convocatoria humana a selección, primer voto pendiente, rechazo de voto duplicado de la misma persona, segundo voto de otra persona, matrícula persistida y resolución desde el endpoint académico de entregas. Una decisión repetida no debe crear otra matrícula ni borrar CRM.

No es una nueva UI de selección ni un E2E de navegador completo. Complementa el registro de navegador y los tests API KAN-182 ya integrados, ejercitando la frontera HTTP del servidor en el Compose desechable.

La preparación `prepare-f2.py` crea la cohorte de referencia y la asignación docente de la prueba si faltan; verifica convocatoria/programa y requiere `GISTAR_ENVIRONMENT=local` más el marcador explícito `GISTAR_E2E_FIXTURE=disposable-synthetic`. El runner requiere URL HTTP local y contraseña sintética en entorno. Su salida se limita a etiquetas de prueba.

Tras arrancar el Compose de pruebas con datos sintéticos (solo entorno propio desechable):

```sh
docker compose -f infra/compose.yaml exec -T -e GISTAR_E2E_FIXTURE=disposable-synthetic api python < e2e/prepare-f2.py
node e2e/f2-admission-enrollment.mjs
docker compose -f infra/compose.yaml exec -T -e GISTAR_E2E_FIXTURE=disposable-synthetic -e E2E_FIXTURE_ID="${E2E_FIXTURE_ID:-local-f2-admission}" api python < e2e/verify-f2.py
node e2e/f2-admission-enrollment.mjs
docker compose -f infra/compose.yaml exec -T -e GISTAR_E2E_FIXTURE=disposable-synthetic -e E2E_FIXTURE_ID="${E2E_FIXTURE_ID:-local-f2-admission}" api python < e2e/verify-f2.py
```

El runner consume `GISTAR_DEMO_PASSWORD`, `GISTAR_API` (localhost:8000 por defecto) y `E2E_FIXTURE_ID` (identificador sintético). El workflow existente prepara la cohorte y ejecuta dos veces el recorrido antes de su limpieza habitual. La segunda vuelta exige que el expediente ya esté admitido, sin duplicados; no recupera silenciosamente un recorrido parcial fallido. Una ejecución local parcial requiere diagnóstico, no reset automático de una base compartida.

Validación local realizada: sintaxis Node, Ruff/compilación de la preparación Python, YAML y diff correctos. No se ejecutó Compose/HTTP contra PostgreSQL localmente. Por petición del usuario no se espera ni comprueba el resultado final de CI. La tarea no se marca Done en Jira.

## EN

Owner Yohanna; sole requested reviewer Anas. Jira deadline **2026-11-25**, next day from this November 24 snapshot, `dev@357cad1`. Independent of pending #121.

This is a real-local-HTTP service journey, not TestClient or mocked routes: public intake, unique dossier, CRM, foreign-program denial, human invitation, first pending approval, same-person duplicate denial, second distinct approval and persisted enrollment resolved through the academic submission endpoint. Repeated admission must preserve enrollment and CRM identities. It complements existing browser registration/API tests; it is not a new selection UI or complete browser journey.

The guarded fixture adds a synthetic reference cohort and a teaching assignment for that cohort. It requires the local environment and an explicit disposable-fixture marker. The runner accepts only a local HTTP API origin and uses environment-provided synthetic credentials. It emits fixed test labels. CI executes it twice before the existing disposable cleanup. The second run verifies the previously completed fixture.

Local Node syntax, Python lint/compilation, workflow YAML and diff checks passed. Docker/database/real HTTP were not run locally, and CI completion is deliberately not checked. No Jira completion or deployment acceptance claimed.

## Independent uniqueness check / Comprobación independiente de unicidad

ES: después de cada ejecución HTTP —incluido su intento de admisión repetida rechazado— `verify-f2.py` abre una sesión PostgreSQL con `SET TRANSACTION READ ONLY`. Consulta **todas** las matrículas vinculadas a la candidatura, no solo la referenciada por la decisión, y exige exactamente una. Comprueba persona/cohorte/estado y vínculo de la decisión. Guarda solo IDs técnicos en un archivo temporal del contenedor desechable y exige los mismos IDs en la segunda vuelta. No modifica la BD. Si se define `E2E_FIXTURE_ID` al ejecutar manualmente, exportarlo para que Node y `docker compose exec -e` reciban el mismo valor; sin definirlo, ambos usan `local-f2-admission`.

EN: after each HTTP run, including the rejected repeat admission, `verify-f2.py` starts a PostgreSQL read-only transaction. It enumerates **all** enrollments linked to the application, not only the decision's reference, and requires exactly one with matching person/cohort/status and decision linkage. Only technical IDs are retained in a temporary file in the disposable container; the second run must preserve them. PostgreSQL is never modified. Export any custom `E2E_FIXTURE_ID` so Node and the exec environment agree; when unset both scripts use the same local default.

Local verifier regressions: four tests cover a valid row, an extra unreferenced row, missing/mismatched identity and changed cross-run IDs without overwriting the baseline. These are pure checks; the PostgreSQL read itself was not run locally. / Cuatro pruebas locales del verificador; consulta PostgreSQL no ejecutada localmente. CI completion is not checked / no se comprueba la finalización de CI.

## Attendance after enrollment (KAN-72) / Asistencia tras la matrícula

ES: La docente asignada crea una sesión de media jornada y registra asistencia online para la matrícula que devuelve la decisión de admisión. El recorrido verifica que captación recibe 403 al leer las sesiones y al intentar escribir un registro. Antes de la primera escritura docente, el resumen cuenta 0,5 días sin dato y cero ausencias injustificadas. Después, devuelve 0,5 días de asistencia online. En la segunda vuelta se exige que la sesión y el registro ya existan y que la misma escritura conserve el identificador y la única revisión. Para ejecutar este incremento, usa una base sintética desechable nueva si la cohorte de una ejecución anterior excluye el día de prueba, 1 de enero de 2026.

EN: The assigned teacher creates a half-day session and records online attendance for the enrollment returned by the admission decision. The journey verifies 403 responses when recruitment staff try to read the sessions or write a record. Before the first teacher write, the summary counts 0.5 unrecorded days and zero unjustified absences. Afterward it reports 0.5 online attendance days. The second run requires the session and record to exist already and checks that repeating the write preserves the record ID and its sole revision. Use a fresh disposable synthetic database if an earlier fixture's cohort dates exclude the test date, 1 January 2026.

Validación KAN-72, 25/11/2026: dos ejecuciones HTTP contra FastAPI y PostgreSQL 16 locales. El verificador de solo lectura confirmó una única matrícula y los mismos identificadores después de cada ejecución. / KAN-72 validation, 2026-11-25: two HTTP runs against local FastAPI and PostgreSQL 16. The read-only verifier confirmed one enrollment and the same IDs after both runs.
