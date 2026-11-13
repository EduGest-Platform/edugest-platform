# F1 — Git, Docker, PostgreSQL y FastAPI · Informe de implementación

**Fecha:** 2026-11-11 (sesión nocturna) · **Alcance:** cimientos F1 locales. Sin push, sin despliegues, sin Jira, sin datos reales. Ninguna contraseña aparece en este informe.

## 1. Resumen ejecutivo

**Estado inicial:** proyecto sin repositorio Git propio (gobernado por un `git init` accidental sin commits en el directorio de usuario de Windows); Docker instalado pero el daemon parado; Compose con credenciales por defecto (`gistar`/`gistar`) y puertos expuestos en todas las interfaces; infraestructura nunca arrancada; pytest y Vitest sin ejecutar (Vitest bloqueado por `EPERM` en la auditoría del 10/11).

**Cambios:** repositorio Git inicializado en la carpeta del proyecto (rama `main`); contraseña aleatoria local de PostgreSQL generada con RNG criptográfico y guardada solo en `infra/.env` y `api/.env` (git-ignorados, con plantillas `.env.example`); Compose parametrizado sin secreto por defecto y con puertos ligados a `127.0.0.1`; stack `db`+`api` construido y arrancado; migración 0001 y seed sintético aplicados; API verificada en vivo (auth, RBAC por rol y por ámbito, candidaturas, auditoría, persistencia); pytest 27/27 y Vitest 16/16 en verde; typecheck y build de producción en verde; **primer commit local seguro creado**. Incidencia resuelta: `src/gistar/config.ts` había sido borrado a la Papelera junto a los stubs de documentación (22:28); restaurado íntegro y verificado.

**Estado final:** cimientos F1 ejecutándose localmente y probados. Pendiente de decisión humana: retirar el `.git` accidental del directorio de usuario, licencia y remoto de GitHub.

## 2. Seguridad de Git

- **Raíz antes:** `git rev-parse --show-toplevel` desde el proyecto devolvía `C:/Users/Admin` (repo accidental, 0 commits). **Raíz después:** `C:/Users/Admin/Desktop/gistar`.
- El `.git` accidental de `C:\Users\Admin` **no fue modificado, movido ni borrado** (su retirada es acción manual de Eli, sección 9). Ninguna operación Git se ejecutó con él como raíz.
- Rama creada: `main` (via `git init -b main`). Identidad: la configuración global existente del equipo (no se inventó ni cambió ninguna).
- **Commit realizado:** `92573a6 — chore: establish project foundation and repository governance` · 138 archivos, ~16 700 líneas, árbol de trabajo limpio después.
- **Sin push** (no hay remoto configurado). Sin hooks ejecutados de terceros.
- Revisión del staging antes del commit: sin `.env` reales, sin venvs (`src/gistar/env/`, `api/.venv/` ignorados), sin `node_modules/` ni `dist/`, sin logs ni backups. Corrección encontrada: el patrón `.gitignore` `.env*` también ignoraba los `.env.example`; se añadió la excepción `!.env.example` y se verificó que los `.env` reales siguen ignorados (`git check-ignore`).

## 3. Infraestructura Docker

- Docker Desktop 29.9.2 estaba instalado (por usuario) pero parado; se arrancó y el daemon respondió en ~5 s.
- Servicios del Compose existente (reutilizado, no reescrito): `db` (pgvector/pg16) y `api` (build de `api/Dockerfile`, python:3.12-slim).
- Cambios en `infra/compose.yaml`: `POSTGRES_PASSWORD` y la URL de la API ahora se interpolan desde `GISTAR_DB_PASSWORD` (en `infra/.env`, obligatorio: `:?`), sin valor por defecto; puertos publicados solo en localhost: `127.0.0.1:5432` y `127.0.0.1:8000`.
- Estado: `db` **Up (healthy)** con healthcheck `pg_isready`; `api` **Up** tras `condition: service_healthy`. Volumen persistente `infra_pgdata` creado y conservado. Imagen `infra-api` construida localmente; nada subido a registries.
- Incidencia: el primer `up` en segundo plano dejó un contenedor `api` a medio crear y el segundo intento chocó por nombre; se eliminó solo ese contenedor duplicado recién creado (sin datos) y el stack arrancó limpio. No se ejecutó ningún comando destructivo de volúmenes.

## 4. PostgreSQL

- Versión: PostgreSQL 16 (imagen pgvector pg16). Compatible con SQLAlchemy 2 + psycopg + Alembic (verificado por la ejecución real de migraciones y pruebas).
- Conexión: OK (el healthcheck y `/health` reportan `database: ok`).
- Migraciones: `alembic upgrade head` aplicado por el contenedor en el arranque (migración `0001_f1_cimientos`, revisada antes: solo `CREATE`, no destructiva; incluye el trigger de solo inserción en `audit_event`). En la base de pruebas, el ciclo `downgrade base → upgrade head` de la sesión pytest funcionó.
- Tablas verificadas indirectamente por las operaciones reales: `person`, `app_user`, `program`, `call`, `application`, eventos CRM y `audit_event`.
- Persistencia: tras `docker compose restart`, la candidatura creada (`IA27A-0007`) seguía recuperable. El seed del arranque es idempotente y no borró datos nuevos.
- Credenciales: usuario `gistar` con contraseña aleatoria de 48 caracteres hex generada con `RandomNumberGenerator`; vive solo en `infra/.env` y `api/.env` (git-ignorados). No se imprimió en terminal, logs ni este informe (los logs del contenedor se leyeron con la URL enmascarada). Base `gistar_test` creada por `infra/initdb/01-test-db.sql`.

## 5. FastAPI

Endpoints del contrato (11) existentes y los siguientes probados en vivo contra `http://127.0.0.1:8000`:

- `/health` → `{"status":"ok","database":"ok"}`.
- `/openapi.json` y `/docs` servidos (contrato regenerable; `pnpm gen:api` ejecutado sin errores).
- **Auth:** login de cuentas sintéticas (`admin@gistar.example`, `docente@…`, `captacion.data@…`) devuelve token opaco; `GET /auth/me` correcto; contraseña errónea → 401; sin token → 401.
- **RBAC:** `docente` → 403 en `/applications` y `/audit-events`; `captacion.data` (ámbito P-DATA) → **403 al leer una candidatura de P-IA** (sin IDOR horizontal); denegación por defecto confirmada.
- **Candidaturas:** `POST /applications` (inscripción pública, datos sintéticos) → 201 con código `IA27A-0007`; recuperación como admin → OK; payload inválido → 422 (validación backend).
- **Auditoría:** `GET /audit-events` (admin) registra `auth.login`, `application.created`, `application.viewed`, con actor, roles y timestamp; el trigger impide UPDATE/DELETE.
- Sin stack traces hacia el cliente en los errores observados (401/403/422 con `detail` limpio); CORS limitado a orígenes localhost; secretos fuera del contrato OpenAPI.
- **Limitaciones:** selección/matrícula, módulo learning, RAG y ML siguen fuera de F1 (pendientes F2+); `POST /applications/{id}/events` y `calls/{id}/summary` solo se cubren vía pytest, no se probaron a mano; logout no probado a mano.

## 6. Pruebas realizadas

| Prueba | Comando o procedimiento | Resultado | Evidencia |
|---|---|---|---|
| Typecheck web | `pnpm exec tsc --noEmit -p tsconfig.json` | **PASS** | salida limpia, exit 0 |
| Unit web | `pnpm test` (Vitest) | **PASS** | 2 files, 16/16 tests, 1.2 s |
| EPERM Vitest (10/11) | reejecución tras reinstalar entorno | **RESUELTO** | no reproducible; era transitorio. El fallo inicial de hoy era por el borrado accidental de `config.ts` (restaurado) |
| Build producción | `pnpm build` | **PASS** | `dist/` generado, 433 kB js |
| Contrato → cliente TS | `pnpm gen:api` | **PASS** | regeneración sin errores |
| Compose config | `docker compose config --quiet` | **PASS** | sin imprimir secretos |
| Stack arriba | `docker compose up -d --build` | **PASS** | `db` healthy, `api` up |
| API pytest | `python -m pytest` (venv, `GISTAR_TEST_DATABASE_URL` desde `api/.env` sin imprimirla) | **PASS** | exit 0; 27 tests (auth 5, applications 6, rbac 10, crm/audit 4, contract 2) |
| Salud API | `GET /health` | **PASS** | `database: ok` |
| Auth + RBAC en vivo | curl con cuentas sintéticas | **PASS** | 401/403/200 según rol y ámbito |
| Alta y lectura de candidatura | `POST/GET /applications` | **PASS** | `IA27A-0007`, 201/200/422 |
| Auditoría | `GET /audit-events` | **PASS** | eventos login/created/viewed |
| Persistencia | `docker compose restart` + relectura | **PASS** | candidatura conservada |
| E2E (`e2e:local`, `e2e:api`) | — | **NOT RUN** | requieren navegador CDP; fuera de esta sesión |
| CI GitHub Actions | — | **NOT RUN** | sin remoto; se ejecutará al publicar |

## 7. Archivos modificados

| Archivo | Cambio | Motivo | Validación |
|---|---|---|---|
| `.git/` (nuevo, en gistar) | `git init -b main` + commit `92573a6` | repo propio seguro | raíz verificada antes y después |
| `.gitignore` | `!.env.example` | el patrón `.env*` ocultaba las plantillas | `git check-ignore` + staging revisado |
| `infra/compose.yaml` | secreto interpolado obligatorio; puertos en 127.0.0.1 | sin secretos por defecto; no exponer servicios | `config --quiet` + stack arrancado |
| `infra/.env.example` (nuevo) | plantilla con receta de generación | documentar el secreto sin revelarlo | revisión manual |
| `infra/.env`, `api/.env` (nuevos, **no versionados**) | contraseña aleatoria local | credenciales robustas solo locales | `git check-ignore`; no impresos |
| `api/.env.example` | placeholder `<GISTAR_DB_PASSWORD>` en las URLs | no sugerir contraseña real de ejemplo | revisión manual |
| `api/README.md` | compose validado, puertos localhost, pruebas leyendo la variable desde `.env` | reflejar procedimiento real sin exponer secretos | comandos ejecutados hoy |
| `commands.md` | sección Estado 11/11 con resultados; pasos de `.env` | evidencia actualizada (constitución E.6) | este informe |
| `README.md` | nota de `.env` locales | arranque reproducible | enlaces verificados |
| `src/gistar/config.ts` | **restaurado desde la Papelera** (borrado 22:28, íntegro: 2 985 bytes) | 12 módulos lo importan; frontend roto sin él | tsc + Vitest + build en verde |
| `api/.venv/` (nuevo, no versionado) | venv con dependencias `[dev]` | ejecutar pytest/uvicorn en host | import check + pytest |

## 8. Riesgos y pendientes

**Bloqueantes (para publicar en GitHub, no para seguir desarrollando):**
- El `.git` accidental de `C:\Users\Admin` sigue existiendo; cualquier comando Git fuera de la carpeta del proyecto opera sobre él (riesgo de añadir archivos personales). Retirarlo es acción manual (sección 9).
- Licencia y nombre del producto sin decidir (PO); el repo no declara licencia a propósito.

**Mejoras recomendadas:**
- Borrar `src/gistar/env/` (venv extraviado de 14 MB, ya ignorado) y vaciar la Papelera solo después de confirmar que no hay nada más que recuperar.
- Ejecutar `pnpm e2e:local` y `e2e:api` cuando haya navegador CDP disponible.
- La CI usa credenciales `gistar/gistar` propias del job (aisladas y efímeras): correcto, pero conviene comentario aclaratorio en `ci.yml`.
- Rotar `GISTAR_DEMO_PASSWORD` (cuentas demo sintéticas) antes de cualquier despliegue.

**Fuera de alcance (F2+):** decisión humana→matrícula, módulo learning/asistencia UI, RAG, ML de abandono, métricas 70%.

## 9. ACCIONES MANUALES NECESARIAS (Elizabeth)

### 9.1 Retirar el repositorio accidental del directorio de usuario
- **Qué:** eliminar la carpeta `C:\Users\Admin\.git` (solo esa carpeta oculta, nada más).
- **Por qué:** es un `git init` accidental sin commits sobre todo tu perfil de Windows; mientras exista, un `git add` ejecutado fuera de `gistar` podría preparar archivos personales.
- **Cómo:** cierra editores/terminales con Git activo → abre PowerShell → `Get-ChildItem C:\Users\Admin\.git -Force | Select-Object -First 3` para confirmar que es un repo vacío (carpetas `objects`, `refs`, archivo `HEAD`) → `Remove-Item C:\Users\Admin\.git -Recurse -Force`.
- **Confirmación:** desde `C:\Users\Admin`, `git status` debe decir «not a git repository»; desde `C:\Users\Admin\Desktop\gistar`, `git log --oneline` debe seguir mostrando `92573a6`.
- **Evita:** borrar cualquier otra cosa de tu perfil; ejecutar el comando desde dentro de `gistar`.
- **Credenciales:** no requiere.

### 9.2 Crear el remoto de GitHub y hacer el primer push (cuando el equipo lo apruebe)
- **Qué:** crear un repositorio privado vacío en GitHub (sin README/licencia autogenerados), añadirlo como `origin` y subir `main`.
- **Por qué:** el commit `92573a6` es solo local; CI y colaboración necesitan el remoto. La licencia debe decidirse antes de hacerlo público.
- **Cómo:** en GitHub → New repository (privado, vacío) → en `gistar`: `git remote add origin <URL>` y `git push -u origin main`.
- **Confirmación:** la pestaña Actions ejecuta el workflow CI; el árbol de archivos coincide con el local; comprueba que **no** aparecen `infra/.env` ni `api/.env`.
- **Evita:** hacerlo público antes de decidir licencia/nombre; subir ramas de prueba; usar credenciales de Somos F5.
- **Credenciales:** tu cuenta personal de GitHub (autenticación local con `gh auth login` o credencial manager; nunca la pegues en el chat).

### 9.3 Guardar y repartir la contraseña local de la base de datos
- **Qué:** la contraseña local de PostgreSQL está en `infra/.env` y `api/.env` (no versionados). Cada miembro del equipo genera **la suya propia** en su máquina copiando los `.env.example` (receta incluida en `infra/.env.example`).
- **Por qué:** sin `infra/.env`, `docker compose` se niega a arrancar (a propósito); no debe circular una contraseña compartida por chats.
- **Confirmación:** `docker compose -f infra/compose.yaml config --quiet` sin error; `git check-ignore infra/.env api/.env` lista ambos.
- **Evita:** pegar el valor en documentos, issues o capturas; reutilizar contraseñas personales.

### 9.4 Vaciar la Papelera (opcional, tras revisión)
- **Qué:** en la Papelera quedan los 4 stubs `.md` que borraste (correcto borrarlos: sus canónicos están en la raíz) y el original de `config.ts` (ya restaurado).
- **Por qué:** higiene; sin urgencia. Ojo: hoy `config.ts` se fue a la Papelera por accidente junto a los stubs — revisa antes de vaciar.

## 10. Resultado final

| Componente | Estado |
|---|---|
| Git local | **READY** (commit `92573a6` en `main`; sin push) |
| Docker | **READY** (db healthy + api up, solo localhost) |
| PostgreSQL | **READY** (16, migrado, seed sintético, persistente) |
| FastAPI | **READY** (health, auth, RBAC, candidaturas, auditoría) |
| Integración API–DB | **READY** (verificada en vivo y por pytest) |
| Pruebas | **PASS** (tsc, Vitest 16/16, pytest 27/27, build; E2E NOT RUN) |
| Preparación para GitHub | **WARNINGS** (retirar `.git` accidental; licencia/nombre del PO; remoto pendiente) |
