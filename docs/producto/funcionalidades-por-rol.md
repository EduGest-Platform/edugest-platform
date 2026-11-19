# Funcionalidades por rol / Features by role

**Estado / Status:** inventario estático del código de `dev` en `c59d201` (19/11/2026). Se ha leído el código (`api/app/core/authz.py`, routers de la API, `contracts/openapi.json`, `src/gistar/config.ts`, `src/gistar/Shell.tsx`); no se ha probado en un navegador. Solo datos sintéticos. / Static inventory of `dev` at `c59d201`; code read, not exercised in a browser. Synthetic data only.

**Leyenda / Legend:**
- **API** = funciona contra FastAPI + PostgreSQL, con permisos comprobados en el servidor / works against the real backend with server-side checks.
- **Pantalla real** = la interfaz usa esa API (modo API) / the UI uses that API.
- **Maqueta** = pantalla de demostración con datos locales (`localStorage`), sin backend / demo screen with local data, no backend.
- **Pendiente** = no existe todavía / not built yet.

## 1. Resumen por rol / Summary by role

| Rol (API → interfaz) | Qué puede hacer hoy de verdad (API) | Pantallas reales | Pantallas maqueta |
|---|---|---|---|
| **Administración** (`admin`) | Todo, en todos los programas: expedientes, CRM, requisitos (incluido publicar el catálogo), preselección y su política, agregados, auditoría | Auditoría | Inicio, calendario, programas, competencias, rúbricas |
| **Captación** (`captacion` → «Personal fundación») | En **su programa**: ver y anotar expedientes (CRM), revisar requisitos y excepciones, prefiltro, cerrar la preselección, **editar la política de silencio**, ver alertas de silencio y agregados | Candidaturas (lista, ficha, CRM, panel de requisitos) | Inicio, calendario, tutoría y alertas |
| **Selección** (`seleccion`) | En **su convocatoria**: lo mismo que captación, salvo editar la política de silencio | Candidaturas | Inicio, calendario |
| **Coordinación** (`coordinacion`) | Agregados por convocatoria sin datos nominales; leer y registrar **excepciones** de requisitos; ver y decidir el cierre de la preselección; ver alertas de silencio | — | Inicio, calendario, cohortes |
| **Docente** (`docente`) | Solo convocatorias que alimentan **su cohorte**: excepciones de requisitos, cierre de la preselección y alertas. **Nada académico todavía** (asistencia, entregas y competencias no tienen tablas) | — | Analítica, alumnado, ficha, competencias, rúbricas, entregas, asistencia, alertas, asistente |
| **Coder** (persona matriculada) | Ver sus propias candidaturas y su sesión (`/me`) | — | Progreso, entregas, asistente |
| **Aspirante** (persona sin rol) | Inscribirse (también sin sesión) y ver sus propias candidaturas | Inscripción, mi candidatura | Inicio, calendario |
| **Sin sesión** | Ver la oferta de convocatorias, inscribirse, iniciar sesión | Inscripción | — |

## 2. Detalle de la API por función / API detail by feature

| Función | Rutas | Quién |
|---|---|---|
| Sesión | `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` | Todas las cuentas |
| Oferta e inscripción | `GET /calls`, `POST /applications` | Público |
| Mis candidaturas | `GET /me/applications` | Aspirante y coder (solo las suyas) |
| Expedientes y CRM | `GET /applications`, `GET /applications/{id}`, `POST /applications/{id}/events` (con resultado del contacto) | Admin, captación (programa), selección (convocatoria). Fuera de ámbito: 403 explicado y auditado |
| Agregados | `GET /calls/{id}/summary` (grupos pequeños suprimidos) | Admin, captación, selección, coordinación |
| Catálogo de requisitos (KAN-135) | `GET/POST /calls/{id}/requirements` | Leer: perfiles con `requirements.read`; publicar: solo admin |
| Revisión de requisitos (KAN-128) | `GET/PUT /applications/{id}/requirement-reviews…`, historial | Cumple/no cumple: admin, captación, selección. Excepciones: también coordinación y docente |
| Prefiltro (KAN-148, KAN-183) | `POST /applications/{id}/requirement-prefilter`, `…/automation-executions…` | Perfiles con acceso a requisitos; **propone revisión humana, nunca decide** |
| Cierre de preselección (KAN-153) | `GET/POST /applications/{id}/preselection-decisions`, `GET /calls/{id}/silence-review`, `GET/PUT /calls/{id}/preselection-policy` | Decidir: los 5 perfiles internos en su ámbito. Política: admin y captación |
| Auditoría | `GET /audit-events` | Solo admin |

Fuera de la API web / outside the web API: carga de documentos del RAG por línea de comandos (KAN-130, `python -m app.modules.knowledge.ingest`) y modelo de abandono offline en `ml/` (KAN-138 y siguientes). Ninguno tiene pantalla ni endpoint todavía.

## 3. Huecos importantes / Main gaps

- **Académico:** no hay tablas ni API de asistencia (KAN-55), entregas (KAN-56) ni competencias (KAN-57). Todas las pantallas docentes y de coder son maqueta. Bloquea KAN-173, KAN-263, KAN-158, KAN-262 y KAN-191. Ver la propuesta de esquema mínimo: [propuesta-esquema-academico-minimo.md](propuesta-esquema-academico-minimo.md).
- **Interfaz de lo ya construido:** no hay pantalla para cierre de preselección, alertas de silencio, política de silencio, catálogo de requisitos ni prefiltro (la API existe). El menú de administración no incluye «Candidaturas», aunque la API se lo permite.
- **Asistente:** la pantalla es maqueta; el RAG tiene la carga (parte A) pero no embeddings (parte B) ni endpoint de preguntas.
- **Personal y permisos:** no hay invitación de personal ni pantalla para asignar o ampliar ámbitos (por ejemplo, ampliar el de un docente); hoy se hace con asignaciones de rol en base de datos.
- **Decisión de admisión, lista de espera y matrícula:** sin implementar (incluida la baja de matrícula decidida el 19/11).

## English summary

Admin can do everything everywhere. Captación works inside its program (applications, CRM, requirement reviews, prefilter, pre-selection closure, silence policy). Selección does the same inside its call, without editing the policy. Coordination sees aggregates and handles requirement exceptions and pre-selection closure. Teachers only reach calls that feed their cohort and have **no academic features yet**, because attendance, submissions and competencies have no tables. Applicants and learners see only their own applications; anyone can browse calls and apply. Real screens today: inscription, my applications, the applications list with CRM and requirement panel, and the audit log; every other screen is a local-data mock. Main gaps: the academic schema (KAN-55/56/57), UI for the features already in the API, the assistant's retrieval and answers, staff invitations and scope management, and the admission → enrolment flow.
