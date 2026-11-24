# KAN-227 — Public course UI / Interfaz pública de formación

## ES

Tarea [KAN-227](https://anasfady87-1789923749606.atlassian.net/browse/KAN-227) asignada a Anas; implementación Yohanna; único revisor solicitado: Anasfady. La descripción propone el 25/11/2026, pero Jira no tiene `duedate`. No se cambia Jira ni se declara aceptación PO.

El backend de KAN-226 ya está integrado. Este stack añade cinco incrementos: cliente público tipado → listado accesible → ficha y lecturas cancelables → conexión a solicitud específica → regresiones y recorrido de navegador. Base inicial `dev`; cada PR siguiente usa la rama anterior. Los componentes intermedios no están disponibles para usuarios hasta integrar el tramo de acceso público.

### Recorrido

En modo API, la pantalla de acceso conserva «Iniciar sesión» y «Quiero inscribirme» y añade «Ver formaciones». El catálogo utiliza solo `/api/v1/public/courses`, con filtro de convocatoria abierta/cerrada, 20 ofertas por página y estados distintos de carga, error y vacío. No recurre al seed del navegador ni transforma un error en una lista vacía.

Cada ficha consulta de nuevo su identificador al servidor. Los nombres se muestran como texto escapado; las fechas de solicitud son fechas de calendario, no instantes convertidos a la zona del navegador. Las plazas son las ofertadas, nunca plazas libres calculadas. No se inventan requisitos, fechas de docencia o garantías de admisión. Una oferta cerrada se puede leer y no muestra «Solicitar plaza».

Las lecturas se cancelan al navegar, cambiar filtro/página o reintentar; un resultado antiguo no publica datos después de cancelar. Mientras cambia la consulta, no se muestra un CTA de una ficha anterior. Foco al título de ficha/listado y al nombre al pasar al formulario; controles nativos con etiquetas y mensajes anunciados.

«Solicitar plaza» reutiliza `InscriptionForm` y el POST existente de candidaturas. No envía automáticamente. Fija la convocatoria elegida y contrasta que siga en el listado de abiertas. Si desaparece, bloquea el envío sin sustituirla por otra. El backend sigue decidiendo autorización, publicación, cierre y duplicados. La prevención cliente no sustituye al servidor ni promete exclusión de carreras entre lectura y envío.

El cliente público no adjunta el token de sesión ni cookies. No cambia permisos ni concede cuentas. El formulario conserva sus campos personales existentes; la creación de cuentas, los campos pendientes KAN-231 y los requisitos editoriales KAN-224 siguen fuera de este incremento. No se añade editor, ruta pública con enlace permanente ni pantalla de catálogo en modo local.

### Evidencia

Vitest comprueba transporte anónimo, filtros, errores, cancelación, escape, fechas, CTA y destino de la solicitud. `e2e/public-catalog.mjs` verifica el recorrido en navegador, recuperación tras bloquear una lectura, teclado, oferta cerrada, foco, convocatoria fijada y envío/repetición. Solo acepta servicios loopback y correos sintéticos `example.test`.

El recorrido se añade al workflow E2E existente sobre Docker desechable y seed sintético; se repite para comprobar la respuesta a duplicados. El harness CDP usa directorio temporal nativo y navegador oculto/headless, compatible con Windows y Linux.

La comprobación local de navegador usa el build real y una doble API sintética temporal: valida interacción y contrato esperado, no persistencia PostgreSQL, integración real ni aceptación del cliente. El recorrido completo contra PostgreSQL/Docker no se ejecutó localmente. Las pruebas, typecheck y build ejecutados se detallan en el informe del último PR. No se espera al CI ni se fusiona o despliega.

Evidencia local del 24/11: `pnpm test` 117 casos PASS; TypeScript y build PASS; cuatro regresiones del verificador E2E PASS. Recorrido con Edge headless y doble API: 19/19 PASS en dos ejecuciones consecutivas; evidencia de la doble: una candidatura, misma convocatoria, sin duplicado adicional. Comprobación visual de catálogo a 390 px y ficha a 1280 px sin desbordamiento horizontal (2/2 PASS). El SQL/backend real no se valida con esa doble.

## EN

KAN-227 is assigned to Anas and implemented by Yohanna; sole requested reviewer Anasfady. Jira describes a proposed 25 November date but has no due-date field. No Jira transition or PO acceptance is claimed.

This five-part stack builds on integrated KAN-226: anonymous typed transport, accessible list, cancellable detail reads, specific application handoff, browser regressions. Review/merge from the `dev`-based root onward.

API login keeps its existing login/general application actions and adds public courses. The server catalogue uses an admission-state filter, 20-item pages and distinct loading/error/empty states, without browser seed fallback. Detail fetches the selected ID again. Names are escaped text, application dates remain calendar dates, capacity is offered capacity, and no requirements, teaching dates, vacancies or admission guarantees are invented. Closed offers remain readable without an application CTA.

Navigation cancels obsolete reads and hides prior-query data/CTAs while loading. Native labelled controls, announced messages and focus movement support keyboard navigation. The CTA pins the selected call in the existing form; a withdrawn target never falls back to a different call. Submission is explicit and uses the existing endpoint. The backend remains authoritative for publication, closure and duplicates.

The public transport sends no session token or cookies. Existing personal fields remain unchanged. KAN-224 editorial acceptance, KAN-231 registration changes, account provisioning, a content editor, permanent detail URLs and a local-mode catalogue are outside scope.

Vitest covers transport, display and lifecycle boundaries. The browser journey checks retry, closed offers, keyboard/focus and the pinned application, including a repeated run. It is added to the existing disposable Docker E2E workflow. Local browser validation uses the real frontend build with a temporary synthetic API double: it proves frontend interaction, not PostgreSQL persistence or end-to-end backend integration. The real Docker/PostgreSQL journey was not run locally. No CI wait, merge or deployment.

Local evidence on 24 November: 117 Vitest cases, TypeScript, build and four E2E-verifier regressions passed. Headless Edge plus the API double passed 19/19 journey checks twice consecutively; the double retained one application for the pinned call. Visual checks at 390 px (list) and 1280 px (detail) had no horizontal overflow (2/2 passed). This does not validate a real backend/database.
