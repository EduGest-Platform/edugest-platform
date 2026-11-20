# KAN-142 — Render feasibility / Viabilidad de Render

**Reviewed / consultado:** 2026-11-17. **Owner / responsable:** Yohanna. **Reviewer / revisión:** Elizabeth.
**Jira deadline / vencimiento:** 27/11/2026; task title requests a decision by 20/11 / el título pide decisión el 20/11. Preserve both; PO must reconcile / conservar ambas hasta aclaración PO.
**Repository snapshot / base:** `dev` `019ab38515f49b2f640df6ebaec09939a203293b`, rechecked / revisado 18/11/2026 after / tras #23. Official provider consultation remains dated 17/11 / consulta del proveedor conserva fecha 17/11.
**Status:** documentary spike completed, recommendation **PROPOSED**; deployment **NOT RUN / BLOCKED by G-ENV and explicit authorization**. / Estudio documental preparado; recomendación propuesta, sin despliegue ni aceptación final.

## Official facts / Hechos oficiales

Shared bilingual table; limits apply at consultation date, recheck before provisioning. / Límites a fecha de consulta, volver a verificar antes de crear recursos.

| Aspect / aspecto | Published limit / límite publicado | Source / fuente |
|---|---|---|
| API idle / inactividad | Sleeps after 15 min; restart about 1 min / suspensión tras 15 min, arranque aprox. 1 min | [Free instances](https://render.com/docs/free) |
| Workspace hours / horas | 750 free service-hours/month shared / 750 horas mensuales compartidas | [Free instances](https://render.com/docs/free) |
| Postgres Free | One active DB/workspace, 1 GB, expires after 30 days / una BD activa, 1 GB, caduca en 30 días | [Free instances](https://render.com/docs/free) |
| DB recovery / recuperación | No managed backups or pooling / sin backups ni pooling gestionados | [Free instances](https://render.com/docs/free) |
| Files / ficheros | Ephemeral; no free persistent disk / efímeros, sin disco persistente gratuito | [Free instances](https://render.com/docs/free) |
| Quota excess / exceso | Billing or suspension/build blocking depends on payment/spend settings / cobro o suspensión según configuración | [Free instances](https://render.com/docs/free) |
| API compute | `free`: 0.1 CPU, 512 MB RAM | [Blueprint reference](https://render.com/docs/blueprint-spec) |
| HTTP binding | `0.0.0.0`, use `$PORT` / escuchar en 0.0.0.0 y PORT | [Web services](https://render.com/docs/web-services#port-binding) |
| PostgreSQL/network | Version 16 supported; same-region internal URL / versión 16 disponible, conexión interna en misma región | [Postgres connections](https://render.com/docs/postgresql-creating-connecting) |
| Vector extension | `pgvector` supported; enable `vector` explicitly / disponible, habilitación explícita | [Extensions](https://render.com/docs/postgresql-extensions) |

La página de [precios](https://render.com/pricing) consultada no expuso en su texto accesible cifras verificables de ancho de banda/minutos de compilación para el workspace del equipo. **No se inventan cuotas ni precios de upgrade.** Deben registrarse desde la documentación/panel aplicable antes de aprobar gasto o publicar. / The accessible pricing page did not establish this team's included bandwidth/build quotas. No account-specific quotas or upgrade prices are invented; verify them before provisioning or spending.

## ES — correspondencia con el repo y riesgos

`render.yaml` propone una API Docker, web estática y Postgres 16 en Frankfurt, acceso externo a BD cerrado y despliegues automáticos desactivados. Son archivos presentes, no recursos creados. La API incorpora el seed sintético en imagen y adapta DATABASE_URL a psycopg; su entrypoint ejecuta migraciones y seed antes de escuchar en `0.0.0.0:$PORT`. La web compila con VITE_GISTAR_API_URL, por lo que fijar/cambiar la URL requiere reconstrucción. CORS debe coincidir exactamente con el origen web autorizado. MLflow permanece local.

Inferencia de viabilidad: **demo F1 pequeña potencialmente viable**, sujeta a pruebas. No hay medición remota de latencia, memoria, tamaño de DB o concurrencia. No asumir que embeddings, ingesta RAG, entrenamiento ML o índices crecientes caben con el mismo plan. David/Abdur deben aportar recursos y tamaños reales antes de ampliar el alcance; entrenamiento y MLflow siguen en entorno local mientras no exista una decisión distinta.

El arranque incluye migración y seed: un tiempo de disponibilidad observado deberá separar provisión/compilación, primera inicialización y reactivación posterior. No presentar la estimación publicada por Render como medición de EduGest. El seed idempotente no es una copia de seguridad ni prueba de recuperación del estado de la demo. Cambiar una contraseña de entorno no rota automáticamente contraseñas de cuentas ya sembradas.

La API actual aún declara contraseña demo fallback y no acredita endurecimiento completo de rate limiting, sesiones o TLS/CORS. Tras #23, el entrypoint usa `--no-access-log` y `core/error_handling.py` añade logs de acceso mínimos, request IDs y respuestas 500 genéricas antes de iniciar la respuesta. Esto es evidencia estática, no certificación de todos los sinks: excepciones después de iniciar la respuesta se relanzan; logger de errores Uvicorn y proxies necesitan comprobación. Aunque el blueprint genere contraseña, **G-ENV sigue pendiente de evidencias y aprobación**. Este estudio no abre el gate ni autoriza uso de datos reales.

## ES — propuesta de ensayo posterior, sin ejecutar

1. **Antes de crear recursos:** Elizabeth acepta presupuesto cero/límites, fecha de creación/caducidad, disponibilidad necesaria para ensayo 09/12 y defensa 10/12; reconcilia decisión 20/11 con vencimiento 27/11. Un recurso iniciado el 20/11 tendría caducidad teórica el 20/12, calculada con la duración publicada; comprobar el instante real en el panel. Esto es planificación, no reserva ni fecha acordada.
2. **Antes de exposición:** autorización explícita, gate G-ENV, secretos independientes no predeterminados, solo cuentas sintéticas, revisión de logs/privilegios y URLs TLS/CORS. Elegir un commit revisado, no una rama mutable sin evidencia.
3. **Tras autorización:** validar Blueprint oficialmente, arrancar y comprobar /health, seed, login y denegación por ámbito. Medir 5 reactivaciones y registrar mediana/máximo, versión, momento y método; no publicar tokens ni credenciales. La validación YAML local no demuestra aceptación o rendimiento de Render.
4. **Capacidad:** registrar uso de DB/índices, conexiones y memoria; contrastar con dashboard del plan. Ejecutar la concurrencia de demo acordada con el equipo y documentar errores; no elegir un objetivo de carga inventado como requisito oficial.
5. **Recuperación:** ensayar recreación desde seed versionado y backup/restauración autorizados del estado sintético en un destino separado; demostrar resultado y duración. No resetear la BD compartida ni abrir acceso externo para facilitar el ensayo sin nueva autorización.
6. **Defensa:** ensayo completo antes de la fecha final y comprobación de salud previa a la sesión. No añadir pings permanentes para eludir el plan. Mantener respaldo Compose local; es contingencia, no sustituye la entrega accesible exigida. Si el ensayo falla, elevar decisión a PO: plan de pago expresamente aprobado u otro destino aprobado, sin migración automática.

## EN — recommendation, risks and acceptance

The existing blueprint proposes Docker API, static frontend and Postgres 16 in Frankfurt, restricted DB ingress and manual deploys. The entrypoint converts the DB URL, migrates/seeds and binds to the platform port. The frontend embeds the API URL at build time; coordinate rebuilds and exact CORS origins. MLflow remains local. These are inspected files, not deployed resources.

Inference: a small F1 demo is a potential fit, not measured capacity. RAG embeddings/ingestion, model training and growing indexes require separate size/resource evidence from David/Abdur. Distinguish provisioning, initial migration/seed and later reactivation in measurements. A repeatable seed is not a backup; environment-secret changes do not rotate already seeded account passwords. Current backend security hardening remains unverified; generating a blueprint password alone does not satisfy G-ENV.

Rechecked against `dev` `019ab38` on 18/11: merged #23 disables Uvicorn access logging in the entrypoint and adds minimal access logs, server request IDs and generic pre-response 500 handling. This is static evidence, not all-sink runtime certification. Exceptions after response start are re-raised; Uvicorn error logging and proxies remain to be checked. No deployment/security gate is opened.

Elizabeth must approve the recommendation, zero-budget boundaries, resource dates and the conflicting planning dates. After explicit deployment/security authorization, validate the Blueprint, verify health/login/denials, measure five reactivations and record method/median/maximum, then test agreed concurrency and inspect resource usage against actual plan quotas. Recreate/restore only into separately authorized synthetic targets; never reset shared data or open DB ingress implicitly. Rehearse before defence; avoid artificial keep-alive traffic. Compose remains a contingency, not a substitute for the accessible hosted deliverable. Any paid plan or alternate provider requires a fresh approved decision.

## Evidence and closing conditions / Evidencia y cierre

- Official pages read on 2026-11-17; links inline / documentación oficial consultada y enlazada.
- Inspected / inspeccionados: `render.yaml`, `api/Dockerfile`, `api/docker-entrypoint.sh`, `api/app/core/{config,db}.py`, existing deployment guide and ADR-0008.
- Local source/link checks only; **no Render CLI/API validation, account, deploy, cold-start benchmark, DB size measurement or restore test executed**. / Solo comprobaciones documentales/locales; sin validación remota, cuenta, despliegue, medición ni restauración.
- [ ] Elizabeth accepts provider/limits and planning dates / acepta proveedor/límites y fechas.
- [ ] Account-specific quotas and resource availability recorded / cuotas y disponibilidad verificadas.
- [ ] G-ENV and explicit deployment authorization recorded separately / seguridad y autorización por separado.
- [ ] Real trial evidence before KAN-142 is treated as runtime-validated hosting / ensayo antes de afirmar viabilidad ejecutada.

No changes to blueprint, permissions, billing, Jira or deployment / no se cambia blueprint, permisos, facturación, Jira ni despliegue.

## RAG follow-up / Seguimiento RAG — 18/11/2026

Source / fuente: [David's review](https://github.com/EduGest-Platform/edugest-platform/pull/21#pullrequestreview-5954254418), ADR-0005 / PR #12. **PROPOSED architecture and author estimates, not a deployed benchmark / arquitectura propuesta y estimaciones del autor, no mediciones de despliegue.**

- ES: Gemini genera embeddings y Groq respuestas mediante HTTP; el diseño no ejecuta un modelo dentro de la API. Un vector de 768 dimensiones ocupa unos 3 KB; David estima unos 3 MB de vectores para 1.000 fragmentos y menos de 10 MB con sus textos. No incluye mediciones de tablas, índices ni sobrecarga PostgreSQL. Propone búsqueda exacta sin HNSW para el corpus inicial; latencia y capacidad siguen sin verificar.
- EN: Embeddings use Gemini and answers use Groq over HTTP; no model is planned inside the API. A 768-dimensional vector is about 3 KB; David estimates about 3 MB of vectors for 1,000 chunks and under 10 MB including text. PostgreSQL table/index/overhead size is not measured. Initial exact search without HNSW is proposed; latency and capacity remain unverified.
- ES: Con `ipAllowList: []`, planificar ingesta dentro del servicio API mediante conexión interna autorizada, sin abrir la BD a portátiles. David prevé idempotencia por hash de contenido; verificar que reinicios no regeneran embeddings ni consumen cuota innecesaria.
- EN: With `ipAllowList: []`, plan ingestion inside the API service over its authorized internal connection, without opening laptop access. David plans content-hash idempotency; verify restarts do not re-embed unchanged content or unnecessarily spend quota.
- ES: Antes del ensayo RAG, revisar la incorporación de `GEMINI_API_KEY` y `GROQ_API_KEY` con `sync: false` al blueprint, sin valores en Git; verificar la migración prevista 0003 y `CREATE EXTENSION IF NOT EXISTS vector` en el destino. Son requisitos futuros, no cambios implementados por este documento.
- EN: Before the RAG trial, review adding `GEMINI_API_KEY` and `GROQ_API_KEY` with `sync: false`, without committing values; verify planned migration 0003 and `CREATE EXTENSION IF NOT EXISTS vector` on the target. These are future requirements, not implementation in this document.
- ES: **Dependencia David, DA6, 25/11:** aportar memoria medida de la API con asistente habilitado, método y versión. Mantener pendiente el dimensionamiento hasta recibirla.
- EN: **David dependency, DA6, 25/11:** provide measured API memory with the assistant enabled, method and version. Capacity sign-off stays pending.
- ES: David retira su propuesta de Neon del ADR-0005. Una BD creada el 20/11 caducaría teóricamente el 20/12 y cubriría la defensa del 10/12; verificar el instante real y margen. La continuidad posterior sigue pendiente de respuesta A11 y decisión PO; no se aprueba otro proveedor.
- EN: David withdraws his Neon proposal from ADR-0005. A DB created on 20/11 would theoretically expire on 20/12 and cover the 10/12 defence; verify the actual timestamp and margin. Post-defence availability remains pending A11 and PO decision; no alternate provider is approved.

Validation / validación: documentation diff and attribution reviewed; no provider calls, ingestion, migration or memory measurement executed / revisión documental y de atribución, sin operaciones remotas ni mediciones.
