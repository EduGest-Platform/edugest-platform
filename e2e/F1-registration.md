# KAN-140 — Registration to dossier / Inscripción a expediente

Owner / responsable: Yohanna. Reviewer / revisión: David; Elizabeth for scope/permissions / ámbitos y permisos.

## ES

Prueba de navegador F1 con el arnés CDP existente, sin añadir dependencias ni reemplazar Playwright. Es un incremento acotado de KAN-140, no el E2E F2/F3 ni la migración completa de YO7 a Playwright.

Usar solo servicios **locales y sintéticos** con seed y convocatoria IA abierta. No ejecutar contra entornos compartidos: la prueba crea una candidatura sintética. Las cuentas usan `GISTAR_DEMO_PASSWORD` no vacía, configurada antes del seed. `CHROME_BIN` debe apuntar al ejecutable Chromium/Chrome. El arnés actual usa Chromium headless sin sandbox: ejecutar únicamente como prueba controlada en runner desechable, sin datos reales.

```sh
WEB_URL=http://localhost:8443/ GISTAR_API=http://localhost:8000 \
E2E_FIXTURE_ID=local-f1-registration node e2e/f1-registration.mjs
```

Exportar previamente contraseña y ruta de Chrome sin publicarlas. La fixture usa correo reservado y un identificador estable: en reejecución se acepta el duplicado esperado y se comprueba que hay exactamente un expediente. No se borra ni reinicia la base local desde el script. CI usa contenedores/volumen desechables y ejecuta el recorrido **dos veces** antes de eliminarlos.

Recorrido: personal captación IA autenticado; inscripción pública en otro contexto; rechazo del mismo correo en mayúsculas; búsqueda y apertura del expediente persistido desde la sesión de personal; captación Data no lo encuentra. Se esperan condiciones de UI con límite temporal, no recuentos globales fijos del seed. No se registran tokens, cuerpos de petición ni capturas con expedientes. Una aserción fallida termina el proceso con error mediante el arnés existente.

Validación local: sintaxis con `node --check`; no se afirma navegador/API local ejecutado (Docker no accesible en esta sesión). El workflow `e2e-f1.yml` aporta ejecución real con PostgreSQL, API, web y Chrome. Revisar Checks del commit. La fixture mínima reutiliza seed F1; no sustituye KAN-79 ni cubre decisiones, matrícula, evaluaciones o coherencia del dataset ML.

## EN

Scoped F1 browser test using the existing CDP harness without new dependencies; this does not complete the YO7 Playwright migration or F2/F3 E2E. Run only on local synthetic services with the seeded open IA call. It creates a reserved-domain application and must not target shared environments. Configure the nonempty demo password before seed, and export the Chrome executable path without publishing credentials. The existing headless harness disables Chromium sandboxing; use controlled disposable runners and synthetic data only.

The stable fixture can be rerun: duplicate registration is expected on repeat runs and exactly one persisted dossier must remain. The script never resets/deletes local data. CI runs twice on disposable PostgreSQL/API/web services then removes volumes. It checks separate public/staff browser contexts, normalized-email duplicates, staff dossier visibility/opening and cross-program search isolation. Bounded UI polling replaces fixed global seed counts. No tokens, request bodies or dossier screenshots are logged.

Local validation covers JavaScript syntax only; see the workflow Checks for actual browser/service execution. Docker was inaccessible in this session. This fixture does not replace the unified KAN-79 seed or test future admission/enrollment/assessment/ML flows.
