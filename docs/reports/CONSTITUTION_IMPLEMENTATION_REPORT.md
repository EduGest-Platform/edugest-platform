# Constitution Implementation Report / Informe de implementación de la constitución

**Fecha:** 2026-11-11 · **Alcance:** solo documentación (sin cambios de código funcional, sin git, sin Jira, sin despliegues).

## 1. Resumen ejecutivo

**Estado inicial.** No existía constitución ni plantilla Spec Kit (`.specify/` ausente). La documentación canónica V3 (`AGENTS.md`, `CLAUDE.md`, `commands.md`, `contribution.md`, `projectplan.md`) vivía dentro de `src/gistar/`, una carpeta de código fuente del frontend. En la raíz, `AGENTS.md` era el documento del scaffold de Figma Make («figma-make-app») y `CLAUDE.md` contenía solo `@AGENTS.md`, de modo que cualquier agente que entrara por la raíz leía el scaffold y **no** las reglas V3: una contradicción estructural real. Había además un virtualenv de Python de 14 MB en `src/gistar/env/` sin regla de `.gitignore`, y `api/README.md` mandaba copiar un `api/.env.example` que no existía.

**Problemas identificados.** (1) Doble `AGENTS.md`/`CLAUDE.md` contradictorios según el punto de entrada; (2) ausencia de constitución; (3) docs de gobierno dentro de `src/`; (4) venv sin ignorar que se versionaría; (5) `.env.example` inexistente; (6) el proyecto **no tiene repositorio Git propio**: el `.git` que lo gobierna es un `git init` accidental, sin commits, en `C:\Users\Admin` (el directorio de usuario completo de Windows).

**Trabajo realizado.** Constitución creada en inglés canónico con traducción española enlazada; `AGENTS.md` V3 consolidado en la raíz fusionando las reglas del scaffold de Figma Make; `CLAUDE.md` raíz reescrito con las notas específicas de Claude; los tres documentos operativos movidos a la raíz con stubs de redirección en `src/gistar/`; `.gitignore` ampliado; `api/.env.example` creado con valores sintéticos verificados contra `api/app/core/config.py`; README con mapa de gobierno y resumen en inglés; validación de enlaces y comandos.

**Estado final:** `READY WITH WARNINGS` — la documentación está lista; el bloqueo es la inicialización de Git (sección 9).

## 2. Inventario de archivos

| Archivo | Estado anterior | Acción | Estado final |
|---|---|---|---|
| `CONSTITUTION.md` | No existía | Creado (EN canónico) | Constitución v1.0 |
| `CONSTITUTION.es.md` | No existía | Creado (traducción ES) | Enlazada a la canónica |
| `AGENTS.md` (raíz) | Scaffold Figma Make | Reemplazado por V3 consolidado (v3.1) que absorbe el contenido del scaffold | Canónico para agentes |
| `CLAUDE.md` (raíz) | Solo `@AGENTS.md` | Reescrito con notas Claude + jerarquía | Operativo |
| `commands.md` (raíz) | No existía en raíz | Movido desde `src/gistar/` + nota Git 11/11 | Operativo |
| `contribution.md` (raíz) | No existía en raíz | Movido desde `src/gistar/` sin cambios | Operativo |
| `projectplan.md` (raíz) | No existía en raíz | Movido desde `src/gistar/` sin cambios | Operativo |
| `src/gistar/{AGENTS,CLAUDE,commands,contribution,projectplan}.md` | Canónicos V3 mal ubicados | Convertidos en stubs de redirección bilingües | Apuntan a la raíz |
| `.gitignore` | Sin regla para `src/gistar/env/` | Añadida regla | Venv excluido |
| `api/.env.example` | No existía (README lo citaba) | Creado con valores sintéticos | Comando `cp` del README ya funciona |
| `README.md` | Sin mapa de gobierno ni inglés | Añadida tabla de gobierno + resumen EN | Punto de entrada bilingüe |
| `AUDITORIA_CODEX_ESTADO_ACTUAL.md` | En la raíz | **Sin tocar** (fuente citada por AGENTS.md) | Pendiente no bloqueante: mover a `docs/` |
| `docs/`, `api/README.md`, código, CI | Correctos | Sin cambios | Intactos |

## 3. Cambios realizados y justificación

| Archivo | Cambio específico | Motivo | Impacto |
|---|---|---|---|
| `CONSTITUTION.md` / `.es.md` | Secciones A–H: arquitectura, calidad (incluye «el código debe ser entendible por humanos»), seguridad, IA responsable, Scrum, agentes, marca/licencia, política de idiomas | No existía marco normativo único; el prompt del PO lo exige | Toda regla tiene ahora una fuente canónica en la cúspide |
| `AGENTS.md` raíz | Fusión V3 + detalles únicos del scaffold (oxfmt, `@layer base`, puerto 8443, `.mise.toml`); referencias a la constitución; regla de legibilidad humana añadida al guardarraíl 4 | Un agente que entraba por la raíz leía el scaffold y desconocía los guardarraíles V3 | Elimina la contradicción más grave; ninguna información del scaffold se perdió (fusionada en §3) |
| Stubs en `src/gistar/` | Contenido sustituido por redirección; **ningún archivo eliminado** | Evitar dos copias que diverjan («no crear constituciones contradictorias»); los docs de gobierno no pertenecen al código fuente | Cualquier herramienta que aún lea esas rutas llega a la raíz |
| `.gitignore` | `src/gistar/env/` | Venv de 14 MB se versionaría al crear el repo | Repo publicable sin binarios |
| `api/.env.example` | Variables `GISTAR_*` verificadas contra `config.py` y `compose.yaml` | README ordenaba `cp .env.example .env` sobre un archivo inexistente | Instrucción de arranque reproducible; valores sintéticos documentados como rotables |
| `commands.md` | Nota 11/11 sobre el repo Git accidental en el directorio de usuario | Hallazgo de esta inspección; riesgo real al publicar | El equipo conoce el bloqueo antes de tocar Git |
| `README.md` | Tabla de gobierno + resumen EN | README era solo ES y no enlazaba la jerarquía | Entrada bilingüe conforme a la política de idiomas |

**Decisión técnica sobre la jerarquía.** Se mantuvo la convención de nombres existente (`commands.md`, `contribution.md`, `projectplan.md` en minúsculas) y la estructura de carpetas real (`docs/`, `docs/adr/`); solo se corrigió la **ubicación** (raíz) y se añadió la constitución encima. Estrategia bilingüe elegida: archivos ya bilingües por secciones se conservan tal cual; la constitución usa el patrón canónico + `*.es.md` porque es el documento nuevo de mayor rango y así queda una sola fuente normativa (EN prevalece, como el código).

## 4. Constitución consolidada

Principios: conservar stack React/Vite + FastAPI + PostgreSQL con contrato OpenAPI (A); código inglés, legible por humanos, tipado y probado proporcionalmente al impacto (B); datos sintéticos, secretos fuera del repo, RBAC deny-by-default por rol+ámbito, asistente solo con herramientas de lectura en lista blanca y prohibición de SQL arbitrario de LLM (C); RAG con citas y abstención, ML orientativo con model card, ninguna decisión sensible automatizada (D); Scrum con PO/SM confirmadas, DoR/DoD, nada «hecho» sin evidencia (E); guardarraíles de agentes: inspeccionar antes de tocar, no inventar resultados, sin git/Jira/deploy sin aprobación (F); marca propia sin Somos F5 y sin licencia inventada (G); documentación bilingüe con fuente canónica única (H).

Relación: la constitución fija el **qué**; `AGENTS.md` el **cómo** para agentes (flujos de producto, formato de respuesta, lentes de revisión); `contribution.md` el **cómo** humano (DoR/DoD, ramas, revisores); `commands.md` los comandos con su estado de verificación; `projectplan.md` el calendario y las épicas; `README.md` enlaza todo. `CLAUDE.md` solo añade notas específicas de Claude y remite hacia arriba.

## 5. Contradicciones corregidas

1. **Raíz vs `src/gistar/`:** el `AGENTS.md` raíz (scaffold) ignoraba roles, fechas, guardarraíles y datos sintéticos. Se conservó el V3 como base por ser el acordado por el equipo (11/11) y el scaffold se absorbió como detalle técnico de Figma Make, porque son instrucciones de entorno, no de gobierno.
2. **`CLAUDE.md` raíz (`@AGENTS.md`)** apuntaba al scaffold; ahora apunta a la jerarquía correcta.
3. **Duplicados potenciales:** los cinco documentos V3 existían solo en `src/gistar/`; al moverlos se evitó mantener dos copias editables (stubs no editables por convención declarada en ellos).
4. **README citaba `api/.env.example` inexistente** (vía api/README): resuelto creándolo, no cambiando el README, porque el comando documentado era el correcto.
5. **Roster V2 antiguo:** ya estaba superseded en V3; la constitución §0 lo refuerza («no reasignar roles desde documentos antiguos»).

## 6. Validaciones realizadas

- **Enlaces relativos** de los 15 documentos de gobierno (raíz, stubs, `docs/README.md`, `api/README.md`): script Node de resolución de rutas → `ALL LINKS OK`.
- **Comandos documentados vs reales:** `package.json` expone exactamente `dev, build, preview, format, test, gen:api, e2e:local, e2e:api`; coinciden con README y `commands.md`. Variables de `api/.env.example` contrastadas con `api/app/core/config.py` (prefijo `GISTAR_`, nombres y defaults) y `infra/compose.yaml`.
- **Secretos:** grep de `password|secret|token|api_key` en md/yaml/json/py/ts → solo credenciales sintéticas locales ya documentadas (`gistar/gistar`, `gistar-demo-2026`), etiquetadas como rotables antes de desplegar. Sin rutas personales de Windows en la documentación.
- **Limitaciones:** no se ejecutaron `pnpm test`, pytest, build ni Docker (fuera del alcance documental y sin evidencia previa de entorno); el Markdown se validó por inspección y por el parser de enlaces, no con un linter dedicado. Estado de los comandos sigue siendo el del informe Codex 10/11 (`CODE_PRESENT_NOT_RUN` en su mayoría).

## 7. Pendientes

**Bloqueantes para subir la documentación**
- B1. **Git:** el proyecto no tiene `.git` propio; existe un repo accidental sin commits en `C:\Users\Admin` (todo el directorio de usuario). Eli (propietaria del Git local según `commands.md`) debe ejecutar `git init` dentro de `Desktop\gistar` y eliminar el `.git` accidental del directorio de usuario. Sin esto no hay nada que publicar.

**No bloqueantes**
- N1. `src/gistar/env/` (venv 14 MB): ya ignorado; conviene borrarlo (requiere aprobación para eliminar).
- N2. `AUDITORIA_CODEX_ESTADO_ACTUAL.md` en la raíz: mover a `docs/auditorias/` y actualizar la referencia en `AGENTS.md` §2 (no se movió por la regla de no eliminar/mover archivos preexistentes sin aprobación).
- N3. `dist/` existe localmente; ya está ignorado.

**Mejoras futuras**
- M1. Traducciones `*.es.md`/EN completas de `docs/00–03` si el tribunal lo exige (hoy son ES con etiquetas de estado).
- M2. Linter de Markdown/enlaces en CI (`.github/workflows/ci.yml`).
- M3. Añadir `CONSTITUTION` al checklist de PR en `contribution.md` cuando haya plantilla de PR.

**Decisiones que requieren aprobación del Product Owner**
- P1. Licencia del repositorio (hoy: sin licencia = todos los derechos reservados; la constitución §G lo registra).
- P2. Nombre definitivo del producto («Gistar» es provisional).
- P3. Confirmar la estrategia canónico-EN + traducción-ES para futuros documentos de alto rango.
- P4. Borrado del venv N1 y traslado de la auditoría N2.

## 8. Checklist de publicación

- [x] Constitución única, bilingüe y enlazada (EN canónico + ES).
- [x] `AGENTS.md`/`CLAUDE.md` sin contradicciones entre raíz y `src/gistar/`.
- [x] Enlaces internos válidos (verificado por script).
- [x] Comandos documentados coinciden con `package.json` y `api/`.
- [x] Sin secretos reales, solo credenciales sintéticas locales marcadas como rotables.
- [x] Sin rutas personales de Windows en la documentación.
- [x] `.gitignore` cubre venvs, `.env*`, `dist/`, caches.
- [x] `api/.env.example` seguro y existente.
- [x] Sin licencia inventada.
- [ ] `git init` dentro de la carpeta del proyecto (Eli) — **bloqueante**.
- [ ] Revisión del PO de licencia y nombre (P1, P2).
- [ ] Primer commit revisado por una segunda persona antes del push inicial.

## 9. Resultado y recomendación

**`READY WITH WARNINGS`.**

Evidencia: la jerarquía documental es coherente y verificada (enlaces, comandos, variables, ausencia de secretos), las contradicciones entre el scaffold y las reglas V3 están eliminadas y la constitución cubre los seis bloques exigidos más legibilidad humana del código. No es `READY FOR GITHUB` porque (1) no existe repositorio Git del proyecto —solo el accidental del directorio de usuario, que además haría que un `git add` arrastrara todo `C:\Users\Admin`— y (2) licencia y nombre del producto esperan decisión del PO. Resuelto B1 y revisadas P1–P2, la documentación puede publicarse tal cual.
