# KAN-238 / KAN-248 — Portfolio scope and limits / Alcance y límites del portfolio

**Snapshot / Instantánea:** 23/11/2026, `dev@112c33d`. **Owner / Responsable Jira actual:** Yohanna. **Requested reviewer / Revisor solicitado:** Anas. **Deadline:** 27/11/2026, not overdue / no vencido. Jira descriptions retain an older David ownership proposal; actual assignee was checked without editing Jira / las descripciones conservan una propuesta antigua de David; se verificó el assignee actual sin editar Jira.

## ES — Alcance verificable (KAN-238)

El consumidor integrado de #7 lee un enlace y devuelve metadata mínima. No es una ingesta de entregas, una evaluación de competencias ni una conexión del asistente. El alcance OBJ del producto sigue sujeto a capacidad y aceptación; este PR solo especifica y comprueba el adaptador ya presente.

| Entrada o salida | Comportamiento actual | Evidencia |
|---|---|---|
| Perfil o repositorio GitHub | Se extraen owner/repo, se normaliza sufijo `.git`; subrutas conocidas se reducen al repositorio | [urls.py](../../api/app/modules/integrations/github/urls.py) |
| Enlaces inseguros | Host ajeno, credenciales, puerto y ciertos segmentos inválidos se rechazan antes del transporte | [pruebas](../../api/tests/test_github_integration.py): `test_invalid_link_never_reaches_the_network`, `test_parse_rejects_unsafe_or_malformed_links` |
| Transporte | Host API fijo, solo GET; no sigue redirecciones; token opcional solo en backend | [client.py](../../api/app/modules/integrations/github/client.py) |
| Repositorio | Nombre/URL, descripción, lenguaje, rama, fork/archivado, README existente, fechas y tamaño de muestra de commits | [schemas.py](../../api/app/modules/integrations/github/schemas.py), [service.py](../../api/app/modules/integrations/github/service.py) |
| Perfil | Login/URL, contador público declarado y resumen de repositorios recientes | `ProfileSnapshot` y `_profile` en las fuentes anteriores |
| Muestreo | Solicita una página de 30 commits o 10 repositorios, sin paginación completa | `COMMIT_SAMPLE_SIZE`, `PROFILE_REPO_LIMIT`; no equivalen a total histórico ni a límites de negocio aprobados |
| Repo vacío | Un 409 únicamente en commits significa muestra vacía; 409 de metadata continúa siendo error | `test_empty_repository_409_is_zero_commits_not_a_crash`, `test_409_on_the_repository_itself_is_still_an_error` |
| Errores | Códigos estables: invalid_url, redirected, not_found, rate_limited, auth_error, unavailable, conflict, api_error | [README del consumidor](../../api/app/modules/integrations/github/README.md) |

### Prueba reproducible

```sh
# API dependencies installed in the existing virtual environment; run from repository root.
python -m pytest --noconftest api/tests/test_github_integration.py -k "not default_transport"
```

Ejecutado localmente con el Python del entorno de revisión: **61 casos correctos**. `--noconftest` evita el fixture global que reinicia PostgreSQL: estos casos solo usan transporte simulado y no llaman a la API web. Se excluye el caso del transporte por defecto, que abre un servidor local para probar redirecciones; esa prueba no se declara ejecutada aquí. Esto no prueba GitHub real, permisos del producto ni datos persistidos. No se esperó a CI.

### Criterios de aceptación de este incremento

- Las fuentes y los casos de prueba permiten reproducir cada afirmación de la matriz.
- Un enlace rechazado no provoca transporte; 404 y errores no se traducen arbitrariamente en actividad cero.
- La salida no incluye mensajes ni identidades de autores de commits. Sin embargo login, URL y descripción de repositorio pueden identificar personas o contener texto libre: **metadata mínima no es anonimización**.
- La existencia de README es un booleano: no se ingiere su contenido, archivos, código, issues, PR ni entregas.
- No se afirma completada la historia de portfolio ni la dependencia PF2-EDU-03.

## ES — Límites y backlog propuesto (KAN-248)

| Prioridad propuesta | Trabajo pendiente | Gate o evidencia antes de aceptar |
|---|---|---|
| P0 | Definir PortfolioLink, titular y autorización para vincular/quitar un enlace | Decisión PO; consentimiento/expectativa de privacidad, alcance persona/cohorte y prueba de acceso horizontal |
| P0 | Definir persistencia y endpoint backend con OpenAPI | Migración reversible, cliente generado, pruebas 401/403 y auditoría mínima; no confiar en la UI |
| P0 | Proyectar errores seguros al producto | Mensajes estables; no filtrar tokens, respuestas crudas, destinos de redirect ni existencia de repos privados |
| P1 | Acordar caché, actualización y cuotas por usuario/ámbito | Datos de prueba y prueba de expiración/rate limit; sin valores de cuota externa asumidos |
| P1 | Acordar paginación, obsolescencia y fecha de captura | Diferenciar muestra de total y dato ausente de cero; fixtures de páginas y fallos parciales |
| P1 | Minimización y retención | Revisar descripción/login/URL como datos potencialmente identificativos; definir borrado y visibilidad |
| P2 | Integración con entregas/cohortes cuando exista contrato aceptado | Revisar PF2-EDU-03/#97 y volver a comprobar su estado; no hacer scraping ni ejecutar código |
| Fuera de alcance | Puntuar estudiantes por commits o automatizar decisiones | Requeriría requisitos y revisión ética distintos; no se deriva de este consumidor |

No hay router de GitHub montado en [main.py](../../api/app/main.py), entidad PortfolioLink ni persistencia de esta instantánea en la base examinada. No se almacenan enlaces ni se habilitan permisos en este PR. El adapter limita destinos solicitados, pero eso no acredita autorización de acceso a expedientes ni ownership del enlace.

Un timestamp de push, repositorio privado/no encontrado, lenguaje o contador de commits no demuestra aprendizaje, autoría, calidad ni ausencia de actividad. No convertir errores o campos ausentes en sanciones. La revisión técnica de Anas no sustituye decisiones PO/privacidad ni el gate de capacidad del alcance OBJ.

## EN — Verified scope and reproducible evidence

This documents the already integrated read-only adapter, not a new portfolio feature, submission ingestion or assistant tool. Current Jira assignee is Yohanna despite stale David proposals in descriptions. Both deadlines are November 27. Product OBJ capacity/acceptance gates remain pending.

`parse_github_url` extracts an owner/repository and rejects unsupported hosts, credentials and ports before transport. The backend client issues GET requests to a fixed API host and refuses redirects. Repository output contains minimal metadata, README existence and commit-sample dates/count; profile output contains public metadata and recent repository summaries. The service requests one page of 30 commits or 10 repositories without complete pagination: samples are not historical totals or approved business limits.

A commits-only 409 represents an empty repository; metadata conflict stays an error. Other typed errors are documented in the consumer README. No README/file/code content, issues, PRs or submissions are ingested. No commit messages or commit-author identities enter the projection, but login, URL and free-text description may identify people: minimization is not anonymization.

The command above passed **61 local fake-transport cases**. `--noconftest` deliberately avoids the global disposable-PostgreSQL fixture for these isolated adapter tests. The default-transport local-server redirect case was excluded and is not claimed as executed. These results do not establish live GitHub integration, product authorization, persistence, release acceptance or CI success. Relative source links were checked and the diff validated; CI completion was not inspected, per user request.

## EN — Proposed backlog and limits

1. **P0:** PO-approved link ownership, consent/privacy expectations, person/cohort authorization and removal, followed by PortfolioLink persistence, reversible migration, OpenAPI/generated client and 401/403/IDOR/audit tests.
2. **P0:** safe product errors without raw provider messages, tokens, redirect destinations or private-repository existence leaks.
3. **P1:** agreed caching, refresh, quota policy, pagination, freshness and missing-versus-zero semantics with deterministic fixtures. No assumed external quota numbers.
4. **P1:** approved retention/deletion and visibility for potentially identifying login, URL and description.
5. **P2:** submission/cohort integration only after an accepted PF2-EDU-03 contract; recheck pending #97. No scraping or code execution.
6. **Excluded:** grading learners by commit counts or deriving automated adverse decisions. Push dates, languages, private/not-found repositories and sample size do not demonstrate learning, authorship, quality or lack of activity.

The inspected baseline mounts no GitHub router and persists no PortfolioLink/snapshot. Requested-destination restrictions do not prove product scope authorization or link ownership. This PR enables neither account linking nor additional permissions. Anas's technical review does not replace PO/privacy acceptance or capacity approval. Jira is unchanged.
