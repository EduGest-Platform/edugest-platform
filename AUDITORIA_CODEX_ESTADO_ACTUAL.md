# Auditoría técnica independiente · estado actual de Gistar

Fecha de auditoría: 10 de noviembre de 2026  
Repositorio auditado: `C:\Users\Admin\Desktop\gistar`  
Naturaleza: auditoría read-only. No se modificó código, configuración, dependencias, base de datos, ramas ni contenido existente fuera de este informe.

## 1. Resumen ejecutivo

1. La copia auditada contiene una web React 19 + Vite 8 + TypeScript + Tailwind 4, no Next.js ni Astro.
2. También contiene un backend FastAPI + SQLAlchemy + Alembic y un esquema PostgreSQL para el incremento F1.
3. La web tiene dos fuentes: modo local con `localStorage` y modo servidor para inscripción, candidaturas/CRM, sesión y auditoría.
4. La cadena servidor verificable está acotada a identidad, convocatorias, inscripción, consulta de expedientes, CRM, agregados y auditoría.
5. Competencias, rúbricas, asistencia, entregas, dashboards y alertas existen como prototipo local; no están persistidos en la API.
6. El asistente es un mock de respuestas; no hay RAG, consulta controlada a PostgreSQL ni feedback IA operativo.
7. La decisión recomendada es **MANTENER el frontend actual**; migrar a Astro añadiría riesgo sin resolver las brechas funcionales.
8. TypeScript pasa en esta auditoría; Vitest no arrancó por `EPERM` al crear un temporal de Vite en `node_modules`.
9. Las pruebas API no se ejecutaron: falta el entorno virtual del proyecto y requieren PostgreSQL; no se levantaron servicios.
10. Bloqueos principales: conectar el recorrido aspirante → decisión → matrícula, persistir el módulo académico y decidir un alcance realista para IA/RAG.
11. La fecha de entrega del 1–4 de diciembre deja poco margen para una migración tecnológica no justificada.

## 2. Alcance, fuentes y limitaciones

### Fuentes examinadas

- Código de `src/`, `api/`, `contracts/`, `e2e/` e `infra/`.
- `package.json`, `pnpm-lock.yaml`, `api/pyproject.toml`, `tsconfig.json`, `vite.config.ts`.
- `README.md`, `api/README.md`, `AGENTS.md`, `docs/00-diagnostico.md`, `docs/01-gap-to-be.md`, `docs/02-arquitectura-y-contratos.md`, `docs/03-plan-equipo-pruebas-riesgos.md`, ADR 0001–0004 y `docs/incrementos/F1-cimientos.md`.
- Migración Alembic, routers, modelos, servicios, pruebas y contratos OpenAPI.
- Metadatos bajo `.figma/`; no se accedió a un archivo o proyecto visual de Figma externo.

### Limitaciones

- No existe una carpeta `.git` en la copia auditada. Por ello no se puede verificar rama, commit, historial, cambios locales ni ficheros sin seguimiento; las referencias a `main`, `f1-cimientos` y commits en la documentación son solo evidencia documental.
- No se recibió el briefing del cliente ni un enlace/archivo de diseño Figma comparable. Las diferencias código–Figma quedan indeterminadas.
- No se levantaron Docker, PostgreSQL, FastAPI, Vite ni un navegador automatizado.
- No se leyeron valores de `.env`, tokens, contraseñas ni secretos. El informe no reproduce credenciales documentadas.
- Los resultados históricos incluidos en la documentación se etiquetan como “documentado previamente”, no como verificados de nuevo.

### Comprobaciones ejecutadas

| Comprobación | Resultado |
|---|---|
| `pnpm exec tsc --noEmit -p tsconfig.json` | **PASA**; código de salida 0 |
| `pnpm test` | **NO VERIFICADA**: Vite falló con `EPERM` al escribir `node_modules/.vite-temp/...` antes de cargar Vitest |
| Pytest API | **NO EJECUTADA**: no existe `api/.venv`; la suite requiere PostgreSQL |
| `docker --version` | Docker disponible: `29.9.2`; no se ejecutó compose |
| `git status`, `git log` | **NO VERIFICABLES**: no existe `.git` en la ruta auditada |
| Build frontend | No ejecutado: podría escribir artefactos; existe evidencia histórica documental de un build correcto |
| E2E | No ejecutado: requiere servicios o un navegador/URL ya servido |

## 3. Estado de Git y mapa del repositorio

### Estado Git

La ruta contiene `AGENTS.md`, `.github/`, `.figma/`, `api/`, `contracts/`, `docs/`, `e2e/`, `infra/`, `public/` y `src/`, pero no contiene `.git`. No es posible afirmar rama, último commit, modificaciones o estado de seguimiento.

### Mapa

```text
src/                  React/Vite: shell, vistas, dominio local, seed y cliente API
api/                  FastAPI, SQLAlchemy, Alembic, modelos, routers y pytest
contracts/            OpenAPI versionado
e2e/                  recorridos CDP en modo local y API
infra/                compose PostgreSQL/pgvector + API e initdb
docs/                 diagnóstico, GAP, arquitectura, ADR y plan por incrementos
.github/workflows/    CI web + API
.figma/               metadatos y comandos de Figma Make
```

`AGENTS.md` sí es una instrucción operativa real para el proyecto Figma Make. `CLAUDE.md` solo contiene una referencia a `AGENTS.md`; no se encontró otra configuración de agentes.

## 4. Stack real detectado y scripts

| Capa | Evidencia | Estado |
|---|---|---|
| Frontend | `package.json`, `src/main.tsx`, `vite.config.ts` | React 19, Vite 8, TypeScript 5.7, Tailwind 4 |
| Backend | `api/pyproject.toml`, `api/app/main.py` | FastAPI, Uvicorn, SQLAlchemy 2, Pydantic 2 |
| Datos | `api/alembic/versions/0001_f1_cimientos.py`, `infra/compose.yaml` | PostgreSQL 16; pgvector aparece en la imagen, no usado aún por código RAG |
| Contrato | `contracts/openapi.json`, `src/shared/api/schema.gen.ts` | OpenAPI → `openapi-typescript` |
| Tests | `src/gistar/__tests__`, `api/tests`, `e2e/` | Vitest, pytest y CDP; Playwright queda mencionado como futuro |
| CI | `.github/workflows/ci.yml` | jobs web/API declarados; no ejecutados en esta auditoría |

Scripts relevantes: `dev`, `build`, `preview`, `format`, `test`, `gen:api`, `e2e:local` y `e2e:api`. La API documenta `uvicorn app.main:app --reload`, Alembic y un seed sintético. Compose está definido, pero no fue validado en ejecución.

## 5. Inventario funcional con evidencias

Estados: **IMPLEMENTADO Y VERIFICADO**, **IMPLEMENTADO SIN VERIFICAR**, **MOCK / UI / STUB**, **PARCIAL**, **NO ENCONTRADO** o **INDETERMINADO**.

| Módulo | Estado | Evidencia | Brecha principal |
|---|---|---|---|
| Frontend y navegación | IMPLEMENTADO SIN VERIFICAR | `src/App.tsx`, `src/gistar/Shell.tsx`, `src/gistar/config.ts` | No se pudo hacer recorrido navegador actual |
| Login y sesión | PARCIAL | `api/app/modules/identity/router.py`, `src/shared/api/session.tsx` | Solo cuentas sintéticas; ejecución no validada |
| Inscripción | PARCIAL | `src/gistar/views/api/ApiAdmissions.tsx`; `POST /api/v1/applications` | API sí crea/reutiliza persona y candidatura; modo local sigue editando demo |
| Validación de formulario | IMPLEMENTADO SIN VERIFICAR | HTML en `ApiAdmissions.tsx`; esquemas Pydantic en `api/app/modules/admissions/schemas.py` | Falta verificación E2E actual |
| Persistencia de candidaturas | IMPLEMENTADO SIN VERIFICAR | `Application`, `Person`, `ApplicationEvent`; migración 0001 | Requiere PostgreSQL en ejecución |
| API FastAPI | IMPLEMENTADO SIN VERIFICAR | `api/app/main.py` y routers identity/catalog/admissions/audit | No arrancada |
| Modelo y migraciones PostgreSQL | IMPLEMENTADO SIN VERIFICAR | `api/alembic/versions/0001_f1_cimientos.py` | `upgrade/check/downgrade` no ejecutados ahora |
| Autenticación | IMPLEMENTADO SIN VERIFICAR | token opaco, hash y sesión en `core/security.py`/identity router | Sin prueba actual de expiración/logout |
| RBAC rol + ámbito | IMPLEMENTADO SIN VERIFICAR | `api/app/core/authz.py`; filtros SQL en admissions | Cobertura existente documentada, no reejecutada |
| Ingesta web/HubSpot/Sheets/asociaciones | PARCIAL | Formulario web y seed; docs excluyen HubSpot en vivo | No hay conectores ni importador confirmado |
| CRM y trazabilidad de candidatura | IMPLEMENTADO SIN VERIFICAR | `ApplicationEvent`, `POST .../events`, auditoría | No hay cambios de etapa/decisión de F2 |
| Preselección por reglas / automatización 70 % | NO ENCONTRADO | Docs lo dejan para F2/F5 | Sin inventario de tareas, medición ni dataset de 100 casos |
| Decisión humana y matrícula | NO ENCONTRADO como flujo completo | `Enrollment` existe; comentario de modelo indica F2 | Falta revisión, decisión, firmas, waitlist y creación desde admisión |
| Competencias y rúbricas | MOCK / UI / STUB | `src/gistar/domain.ts`, `Catalog.tsx`, `Rubrics.tsx` | Estado solo en localStorage; no routers/modelos API académicos |
| Asistencias | MOCK / UI / STUB | `AttendanceModal.tsx`, `seed.json`, `domain.ts` | No existe persistencia/API de sesiones y registros |
| Entregas y portfolios | MOCK / UI / STUB | `Deliveries.tsx`, `ReviewModal.tsx`, `repositorio_ficticio` | URLs ficticias; no integración GitHub ni almacenamiento de evidencias |
| Dashboards cohorte/tutoría | MOCK / UI / STUB | `Dashboard.tsx`, `GroupAnalytics.tsx`, `metrics.ts` | Cálculo cliente sobre seed/localStorage; no agregados académicos servidor |
| Asistente | MOCK / UI / STUB | `Assistant.tsx`, `seed.json:2060`, `types.ts` | Tres respuestas fijas; no RAG ni consulta operativa PostgreSQL |
| RAG | NO ENCONTRADO | Docs lo planifican para F4; no hay módulo knowledge | Faltan corpus, chunks, embeddings, filtro, citas y abstención |
| Alertas de abandono | MOCK / UI / STUB | `domain.ts`, `FollowUp.tsx`, `alertas_simuladas` | Regla explicable local; no modelo, API, intervención ni auditoría servidor |
| Feedback asistido | MOCK / UI / STUB | `seed.json`, `ReviewModal.tsx` | Texto semilla; no generación ni borrador persistido con revisión |
| Errores | PARCIAL | `errorMessage`, notices y respuestas HTTP | Varias cargas API no muestran error; falta estrategia transversal |
| Observabilidad | PARCIAL | `/health`, `audit_event` | Sin métricas, trazas, alertas operativas ni política de logs |
| Datos demo/sintéticos | IMPLEMENTADO SIN VERIFICAR | `src/gistar/seed.json`, `api/app/seed.py`, README | Debe impedirse cualquier despliegue del modo local como producto |
| Tests | PARCIAL | `src/gistar/__tests__`, `api/tests`, `e2e/` | Verificación actual incompleta; no hay `evals/` para IA/70 % |

## 6. Flujos end-to-end y rupturas

### Flujo servidor F1

```text
Formulario React
  → validación HTML/Pydantic
  → POST /api/v1/applications
  → create_application()
  → Person + Application + evento/auditoría
  → ApplicationReceipt
  → pantalla de recibo / refresh de sesión
```

El código necesario está presente en `ApiAdmissions.tsx`, `api/app/modules/admissions/router.py` y `service.py`. No se pudo verificar en ejecución por falta de API/PostgreSQL levantados.

### Consulta/CRM servidor F1

```text
Login → token en sessionStorage → endpoint con Authorization
  → CurrentPrincipal → RBAC por rol/ámbito → filtro SQL
  → ficha / evento CRM → auditoría
```

La cadena está implementada para las vistas declaradas en `src/shared/api/config.ts:9`: `inscripcion`, `candidatura`, `candidaturas` y `auditoria`.

### Ruptura principal de integración

```text
admisión API ──X── decisión humana ──X── Enrollment ──X── aprendizaje API
                                                               └─X── RAG/feedback/riesgo API
```

La web sigue mostrando muchas vistas locales aunque la sesión sea de API. `src/shared/api/config.ts:2` lo declara explícitamente. Esto puede producir una demo con inscripciones servidor y dashboards basados en otro dataset local si no se controla el modo y el alcance de la presentación.

## 7. Código, documentación y Figma

- La documentación es coherente al describir una estrategia incremental: F1 cubre identidad/admisión mínima y F2–F4 quedan pendientes.
- La documentación describe “F1 hecho” y resultados de pruebas previas, pero la copia no contiene Git para corroborar el commit o rama.
- El código confirma que `API_VIEWS` solo cubre cuatro vistas; las vistas académicas siguen usando el store local.
- El modelo `Enrollment` existe, pero su propio comentario indica que se crea a partir de una decisión F2; no hay endpoint de decisión/matrícula.
- `.figma/` contiene metadatos/comandos de Figma Make, no un diseño de Figma inspeccionable. No es posible comparar píxeles, componentes ni sincronización con un briefing.

## 8. Next.js vs Astro vs híbrido

| Criterio aplicado al repositorio | Mantener React/Vite | Migrar a Astro | Híbrido Astro + React/Next |
|---|---|---|---|
| Código reutilizable | Máximo: `src/` ya es React | Requiere adaptar entrada, routing y configuración | Requiere duplicar frontera de apps |
| Estado cliente | Ya existe store, modales y lógica de dominio | React islands conservarían parte, con nueva composición | Más contratos entre superficies |
| Formularios autenticados | API client/session ya conectados | Posible, pero aporta poco para app privada | Complejidad adicional |
| Dashboards interactivos | React ya encaja | Astro no elimina la necesidad de React | Dos runtimes y rutas |
| Tailwind/UI | Ya configurado | Reconfiguración y riesgo de regresión | Configuración duplicada |
| Tiempo restante y equipo de cinco | Menor riesgo | Alto coste sin valor funcional directo | Mayor coste y coordinación |
| Páginas públicas estáticas | Suficiente con Vite actual | Astro sería ventajoso si fueran prioridad real | Solo justificaría una superficie pública grande |
| Despliegue | Ya definido por Figma Make | Nuevo pipeline y compatibilidad por validar | Dos despliegues o una integración compleja |

### Veredicto

**MANTENER React/Vite**, confianza **alta (0,90)**. El repositorio es una aplicación dinámica con sesión, formularios, permisos, dashboards y estado de dominio. Migrar a Astro no resuelve ninguna brecha de persistencia, RBAC, RAG o flujo de admisión y sí introduce riesgo de regresión antes del 1–4 de diciembre.

Revisaría el veredicto solo si el cliente convierte el producto en un sitio mayoritariamente editorial/público y cancela la aplicación autenticada, o si Figma Make deja de ser una restricción real. No hay evidencia para recomendar híbrido: añadiría una frontera tecnológica sin una página pública compleja que lo justifique.

## 9. Arquitectura, dependencias, seguridad y RGPD

### Fortalezas comprobables por lectura

- Monolito modular FastAPI razonable para un equipo pequeño.
- PostgreSQL y Alembic definidos, con restricciones de unicidad y estados.
- Token opaco almacenando solo hash de sesión; expiración y revocación modeladas.
- Autorización servidor por rol y ámbito en `authz.py`; coordinación recibe agregados con supresión.
- Trigger de auditoría de solo inserción en `0001_f1_cimientos.py:186`.
- Contrato OpenAPI versionado y cliente TypeScript generado.
- Datos nominales marcados como sintéticos en la documentación y seed.

### Riesgos objetivos

- `api/app/core/config.py` contiene un valor demo por defecto y `infra/compose.yaml` usa credenciales de desarrollo. Aunque son datos sintéticos, el modo demo no debe exponerse ni reutilizarse en producción.
- El modo local guarda todo en `localStorage` y ofrece selector “Ver como”; no es control de acceso ni persistencia multiusuario.
- La API lista nombre y correo a roles con permiso de expediente; debe mantenerse estrictamente limitada a datos sintéticos y a ámbitos autorizados.
- La búsqueda de expedientes usa coincidencia sobre correo; para producción habría que revisar minimización, enumeración y respuesta genérica a duplicados.
- No se observan rate limiting de login, cabeceras de seguridad, HTTPS, rotación operativa ni retención de sesiones en el código inspeccionado.
- La auditoría API evita texto libre en metadatos, pero la bitácora local es editable y no es evidencia de auditoría.
- Las etiquetas “IA” sobre datos semilla o respuestas mock pueden inducir a una interpretación incorrecta de capacidades.
- No hay módulo de assistant; por tanto todavía no existe la superficie de riesgo SQL/RAG que deberá diseñarse como consultas allowlisted/read-only, filtradas por ámbito antes de recuperar datos.

## 10. Riesgos y bloqueos priorizados

| ID | Riesgo/bloqueo | Prioridad | Impacto |
|---|---|---|---|
| R-01 | No existe flujo operativo completo de decisión humana → matrícula | P0 | Impide demostrar el valor central aspirante → coder |
| R-02 | Módulo académico no persistido en API | P0 | Asistencia, entregas, competencias y dashboards no son multiusuario ni demostrables como producto |
| R-03 | RAG/assistant operativo no existe | P1 | El objetivo de asistente híbrido no puede presentarse como implementado |
| R-04 | Medición del 70 % no existe | P1 | No se puede sostener el porcentaje ni evaluar sesgo/eficacia |
| R-05 | Vitest no arranca en este entorno por escritura temporal EPERM | P1 | Bloquea la regresión local actual hasta resolver permisos/entorno o configurar temporal seguro |
| R-06 | API/DB y compose no verificados en esta auditoría | P1 | El backend documentado puede no estar reproducible en la máquina de demo |
| R-07 | Dos fuentes de datos conviven durante la transición | P1 | Riesgo de demo inconsistente o de interpretar mocks locales como datos servidor |
| R-08 | Falta briefing/Figma comparable | P2 | No se puede confirmar ajuste funcional ni visual al cliente |
| R-09 | Bundle documentado >500 kB | P2 | Carga y mantenibilidad peores, aunque no bloquea la demo |
| R-10 | Seguridad operativa incompleta | P2 | Riesgo si el prototipo se expone fuera de un entorno controlado |

## 11. Backlog técnico sugerido para Jira

| ID | Título y descripción observable | Evidencia | Pri. | Tamaño | Rol sugerido | Dependencias | Criterio de aceptación | Demo |
|---|---|---|---|---|---|---|---|---|
| AUD-001 | Completar decisión humana y matrícula: requisitos, revisión, puntuación versionada, decisión conjunta, reserva y `Enrollment` | SIN EVIDENCIA SUFICIENTE de endpoints; docs/02 lo marca F2 | P0 | L | Backend, PO, QA | F1 API y decisión de negocio | Un caso sintético recorre inscripción → revisión → admitida/reserva/no admitida; solo decisión autorizada crea matrícula y queda auditada | Imprescindible |
| AUD-002 | Persistir académico: cohortes, competencias, rúbricas, evaluaciones, asistencia y entregas | `src/gistar/*`, `api/app/modules/learning/models.py` | P0 | L | Backend, Frontend, QA | AUD-001 | Dos navegadores ven el mismo registro; docente fuera de cohorte recibe 403; historial mantiene versión de rúbrica | Imprescindible |
| AUD-003 | Definir y documentar el MVP con PO, incluyendo si asistente/RAG entra en demo | docs/03: preguntas POR VALIDAR | P0 | S | PO, Scrum Master | Disponibilidad del cliente | Backlog priorizado y firmado con exclusiones explícitas | Imprescindible |
| AUD-004 | Validar reproducibilidad de PostgreSQL, migraciones, seed y compose | `infra/compose.yaml`, `api/alembic/` | P1 | M | Solutions Architect, DevOps, QA | Entorno Docker/PostgreSQL | `upgrade head`, `check`, seed y health pasan en entorno limpio; evidencia adjunta | Imprescindible |
| AUD-005 | Resolver el fallo EPERM de Vitest sin alterar lógica funcional | Resultado actual; `vite.config.ts` | P1 | S | DevOps, Frontend | Permisos/entorno local | `pnpm test` ejecuta y reporta las pruebas; no deja artefactos no deseados en repo | Imprescindible |
| AUD-006 | Eliminar ambigüedad de fuente: indicador visible de modo y bloqueo de vistas locales en demo servidor | `src/shared/api/config.ts:2-9`, ADR-0004 | P1 | M | Frontend, Solutions Architect | AUD-002 | Todas las vistas del recorrido demo muestran la fuente; ninguna mezcla datos local/API | Imprescindible |
| AUD-007 | Diseñar evaluación del 70 % con tareas elegibles, frecuencias y casos sintéticos | docs/01, docs/03 | P1 | M | PO, Data/ML, AI Engineer | Definición del proceso | Informe reproducible con denominador, ≥100 casos sintéticos y revisión humana; no se presenta porcentaje sin evidencia | Imprescindible |
| AUD-008 | Implementar assistant mínimo seguro: corpus autorizado, citas, abstención y consultas SQL allowlisted read-only | No hay módulo `knowledge` ni endpoint operativo | P1 | L | AI Engineer, Backend, Seguridad | Alcance MVP y RBAC académico | Pregunta fuera de ámbito no recupera datos; respuesta válida cita fuente; consulta operativa solo usa métricas permitidas y queda auditada | Condicional |
| AUD-009 | Implementar alerta explicable e intervención revisada, sin decisión automática | `domain.ts`, `FollowUp.tsx`, `alertas_simuladas` | P1 | M | Data/ML, Backend, PO | AUD-002; política ética | Alerta muestra señales, responsable y estado; cerrar/intervenir queda auditado; ninguna baja automática | Condicional |
| AUD-010 | Sustituir feedback “propuesto por IA” mock por borrador etiquetado y publicación tras revisión | `seed.json`, `ReviewModal.tsx` | P2 | M | AI Engineer, QA | AUD-002 y política de revisión | Borrador no se publica automáticamente; publicación requiere persona autorizada y conserva versión | Posponible |
| AUD-011 | Reforzar seguridad de demo y despliegue: rate limit, cabeceras, HTTPS, rotación y retención | `api/app/core/config.py`, docs/03 | P2 | M | DevOps/Seguridad | Entorno de despliegue | Checklist automatizado o evidencias de cada control; demo no usa secretos por defecto | Posponible |
| AUD-012 | Añadir E2E ejecutable en CI para el recorrido prioritario | `e2e/*.mjs`, `.github/workflows/` | P1 | M | QA, DevOps | AUD-004, AUD-005 | CI arranca servicios y prueba inscripción, permisos, decisión y matrícula; artefactos de fallo conservados | Imprescindible |
| AUD-013 | Obtener briefing y referencia Figma verificables y levantar matriz de diferencias | Solo `.figma/` y menciones documentales | P2 | S | PO, Frontend | Acceso a fuente de diseño | Cada pantalla MVP tiene referencia, divergencia y decisión aceptada | Imprescindible |
| AUD-014 | Comprobar integridad de distribución Git y recuperar trazabilidad de rama/commit | `.git` ausente | P1 | S | Scrum Master, Solutions Architect | Acceso al repositorio origen | Entrega contiene `.git` o export verificable con commit, rama y estado; no se sobrescribe trabajo local | Imprescindible |

## 12. Plan mínimo de recuperación del MVP y dependencias

La secuencia debe tratarse como orden de dependencias, no como promesa de fechas de desarrollo:

```text
Decisión de MVP/briefing
        ↓
Validar entorno + migraciones + CI + pruebas
        ↓
Decisión humana y matrícula
        ↓
Persistencia académica y permisos por cohorte
        ↓
Recorrido E2E aspirante → coder → seguimiento
        ↓
Elegir una única capacidad diferenciadora: RAG seguro o riesgo explicable
        ↓
Ensayo de demo + evidencias + respaldo sintético
```

Para una demo estable, priorizar identidad/admisión, decisión humana, matrícula y un mínimo académico persistido. RAG, modelo de riesgo, feedback IA y medición del 70 % deben entrar solo con criterios de aceptación y datos sintéticos reproducibles; si no caben, deben declararse como roadmap y no como capacidades implementadas.

## 13. Preguntas abiertas para PO/cliente/equipo

1. ¿Cuál es el recorrido exacto que debe aprobar la demo: inscripción, preselección, decisión, matrícula y qué seguimiento?
2. ¿Qué significa exactamente “automatizar el 70 %”: tareas, casos, tiempo o decisiones? ¿Cuál es el denominador?
3. ¿Quién puede revisar, firmar y cambiar cada etapa de admisión?
4. ¿La matrícula ocurre desde una decisión admitida? ¿Qué tratamiento tiene la lista de espera?
5. ¿Qué datos académicos son imprescindibles para el MVP: asistencia, entregas, competencias, rúbricas o todos?
6. ¿Qué corpus autorizado y qué roles/cohortes debe cubrir el asistente?
7. ¿Se exige un LLM real o basta una demostración extractiva reproducible con citas?
8. ¿Se acepta que riesgo y feedback sean prototipos explicables sin acción automática?
9. ¿Qué diseño Figma y briefing son la fuente de verdad?
10. ¿Dónde se alojará la demo y quién validará PostgreSQL, Docker, CI y respaldo?
11. ¿Qué política de retención, minimización y supresión se aplicará incluso a datos sintéticos?
12. ¿Se entregará el repositorio Git completo con rama y commit trazables?

## 14. Anexo de evidencias

| Evidencia | Ruta |
|---|---|
| Fuente API/local | `src/shared/api/config.ts:2-9` |
| Store y persistencia local | `src/gistar/store.tsx:8-62` |
| Tipos de mocks | `src/gistar/types.ts:247-274` |
| Seed de entregas, alertas y RAG mock | `src/gistar/seed.json:1821-2086` |
| Frontend API de admisiones | `src/gistar/views/api/ApiAdmissions.tsx` |
| Router de admisiones | `api/app/modules/admissions/router.py:45-112` |
| Auth y sesión | `api/app/modules/identity/router.py:40-73`, `api/app/core/security.py` |
| RBAC | `api/app/core/authz.py` |
| Auditoría | `api/app/core/audit.py`, `api/app/modules/audit/router.py` |
| Esquema y trigger append-only | `api/alembic/versions/0001_f1_cimientos.py:1-186` |
| Matrícula aún sin flujo de decisión | `api/app/modules/learning/models.py:10-19` |
| Contrato | `contracts/openapi.json`, `src/shared/api/schema.gen.ts` |
| Pruebas frontend | `src/gistar/__tests__/flows.test.ts`, `migrate.test.ts` |
| Pruebas API | `api/tests/` |
| E2E | `e2e/local-mode.mjs`, `e2e/f1-api-mode.mjs` |
| Infra | `infra/compose.yaml`, `infra/initdb/01-test-db.sql` |
| CI | `.github/workflows/ci.yml` |
| Evidencia histórica | `docs/00-diagnostico.md`, `docs/incrementos/F1-cimientos.md` |

### Comandos de inspección utilizados

```text
Get-ChildItem / rg --files
Get-Content
rg -n
docker --version
pnpm exec tsc --noEmit -p tsconfig.json
pnpm test
```

No se ejecutaron `git` contra un repositorio inexistente, `docker compose`, instalaciones, migraciones, servidores, despliegues ni peticiones externas.

## HANDOFF_A_SCRUM_PO

| Qué está hecho | Qué falta | Qué bloquea | Qué decidir | Qué priorizar en el siguiente sprint |
|---|---|---|---|---|
| Web React/Vite; modo local; F1 de API con identidad, candidaturas, CRM, RBAC y auditoría definido en código; seed sintético; CI declarada | Flujo decisión→matrícula; académico persistido; E2E/entorno verificable; RAG, riesgo, feedback y medición 70 % | No hay recorrido completo aspirante→coder ni evidencia actual de ejecución API | Alcance MVP, firmantes, definición del 70 %, necesidad real de IA y fuente Figma/briefing | Validar entorno y Git; cerrar MVP; completar AUD-001/AUD-002; resolver AUD-005; automatizar AUD-012 |

