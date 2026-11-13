# Constitución del proyecto — Gistar (nombre provisional) · Proyecto Final 2 de Somos F5

> **Versión 1.0 · 2026-11-11 · Traducción al español.** La versión canónica es [CONSTITUTION.md](CONSTITUTION.md) (inglés); si las versiones difieren, prevalece la inglesa.
>
> Esta constitución es la cúspide de la jerarquía documental. El detalle operativo está en [AGENTS.md](AGENTS.md) (agentes de IA), [contribution.md](contribution.md) (flujo humano), [commands.md](commands.md) (comandos), [projectplan.md](projectplan.md) (hoja de ruta) y [README.md](README.md) (punto de entrada). Esos documentos desarrollan esta; nunca pueden contradecirla.

## 0. Propósito y alcance

Una única plataforma web accesible y auditable para el recorrido completo del estudiante: catálogo público → inscripción → preselección → selección con **decisión humana** → matrícula → formación por cohortes → acompañamiento docente, asistente de recuperación (RAG) e indicadores de riesgo supervisados. Aplica a toda persona o agente de IA que trabaje en este repositorio.

**Hitos de entrega:** congelación de desarrollo **04-12-2026**, ensayo de defensa **09-12-2026**, defensa final **10-12-2026**.

**Equipo:** Yohanna (Scrum Master + automatización), Elizabeth (Product Owner + backend/PostgreSQL/FastAPI), Anas (frontend), David (RAG/asistente), Abdur (ML de prevención del abandono, exclusivamente). No reasignar roles a partir de documentos antiguos.

## A. Arquitectura y reutilización

1. Conservar el stack existente: **React 19 + Vite 8 + TypeScript + Tailwind CSS 4** (web, en la raíz tal como lo ejecuta Figma Make), **FastAPI + SQLAlchemy 2 + Alembic** (`api/`), **PostgreSQL 16** como fuente de verdad de los datos operativos.
2. El contrato de la API es **OpenAPI** (`contracts/openapi.json`); el cliente TypeScript se genera desde él (`pnpm gen:api`). Backend y frontend nunca se desvían del contrato en silencio.
3. Separación clara entre presentación (`src/`), dominio/API (`api/app/modules/`), persistencia (modelos SQLAlchemy + migraciones Alembic) y componentes de IA.
4. Los cambios de base de datos solo mediante **migraciones Alembic versionadas**, reversibles cuando sea posible. Sin deriva de esquema ni modelos de datos duplicados.
5. Sin refactorizaciones masivas, migraciones de framework (ni Astro ni Next), reestructuración de la raíz, microservicios ni nueva infraestructura sin un ADR aprobado en `docs/adr/` que demuestre necesidad técnica objetiva y con las comprobaciones en verde.
6. Preservar la compatibilidad con Figma Make mientras se use: `.figma/`, plugins de `vite.config.ts` y alias `@`, `.mise.toml`, Tailwind v4 vía `src/index.css`.

## B. Calidad del código

1. **Todo el código y sus identificadores en inglés**: variables, funciones, clases, rutas, endpoints, campos de esquema y pruebas. Los textos de la interfaz siguen el idioma del producto.
2. **El código debe ser entendible por humanos.** Nombres claros, funciones y módulos pequeños con una sola responsabilidad, y comentarios solo donde el código no pueda explicarse por sí mismo. La legibilidad gana a la astucia.
3. Tipado estático donde el lenguaje lo permita (TypeScript estricto en la web, Python tipado/Pydantic en la API).
4. El backend valida todas las entradas; los errores se gestionan de forma explícita, nunca se silencian.
5. Pruebas proporcionales al impacto: unitarias (Vitest, pytest), de integración y al menos una E2E por flujo crítico; todo cambio sensible a RBAC incluye una prueba de autorización positiva y otra negativa.
6. Las nuevas dependencias exigen justificación escrita; proteger la compatibilidad con la funcionalidad existente.

## C. Seguridad y privacidad

1. **Datos exclusivamente sintéticos** durante el desarrollo y las demos. Nunca datos reales de estudiantes.
2. Los secretos nunca entran en el repositorio. Las variables de entorno se documentan con archivos de ejemplo seguros (`api/.env.example`); las credenciales de demo son sintéticas y se rotan antes de cualquier despliegue.
3. Autorización en el backend, **denegación por defecto**, por rol + acción + ámbito (programa/convocatoria/cohorte). Ocultar la interfaz no es seguridad; comprobar 401/403 y accesos horizontales (IDOR).
4. Mínimo privilegio en todo; las operaciones relevantes (firmas de admisión, cambios de acceso, correcciones de asistencia, comentarios privilegiados) quedan auditadas.
5. Minimización de datos: registrar solo lo necesario; sin datos personales en prompts ni logs de modelos.
6. El asistente accede a PostgreSQL **solo mediante funciones backend de solo lectura en lista blanca**. Un LLM nunca ejecuta SQL arbitrario, nunca recibe una URL o credencial de base de datos y nunca elige su propio ámbito.
7. Prohibido publicar información privada o credenciales, en código, documentación, issues o transcripciones.

## D. IA responsable

1. Las respuestas RAG proceden de documentos autorizados y filtrados por ámbito, con citas de fuentes y **abstención** cuando falta evidencia; nunca fabricar datos ni ceros.
2. Las respuestas documentales (RAG) y las consultas de datos operativos (herramientas de solo lectura) son caminos separados, ambos a través del backend.
3. Evaluar fidelidad y afirmaciones no sustentadas antes de presentar funciones del asistente como operativas.
4. El ML de abandono es **solo orientativo**: datos sintéticos de entrenamiento documentados, métricas, model card y limitaciones. El feedback redactado por IA requiere aprobación docente antes de publicarse.
5. Revisión humana de toda alerta y resultado sensible. **La IA nunca automatiza decisiones de admisión, exclusión, expulsión, sanción o abandono sobre personas.**
6. Registrar versiones de modelos, rúbricas, prompts y decisiones relevantes.

## E. Colaboración y Scrum

1. La Product Owner (Elizabeth) ordena y acepta el Product Backlog; el equipo acuerda el Sprint Goal y el Sprint Backlog; la Scrum Master (Yohanna) facilita los eventos y elimina impedimentos.
2. Un responsable principal por historia más una persona revisora distinta; Definition of Ready y Definition of Done según [contribution.md](contribution.md).
3. Criterios de aceptación medibles; integración frecuente mediante PR pequeños; sin merge directo a `main` sin revisión.
4. Los impedimentos y decisiones se documentan (ADR, registros de incremento en `docs/`).
5. Prioridad a los incrementos funcionales verificables frente a pantallas de demo sin backend.
6. **Ninguna tarea se marca como completada sin evidencia** (comandos ejecutados, fechas, resultados). Bloqueado o no ejecutado nunca es «hecho». Etiquetas de estado: `VERIFIED_RUNNING`, `CODE_PRESENT_NOT_RUN`, `MOCK`, `PROPOSED`, `BLOCKED`.

## F. Trabajo con agentes de IA

Guardarraíles explícitos para Claude, Codex y cualquier otro agente (detalle operativo en [AGENTS.md](AGENTS.md)):

1. Leer las instrucciones relevantes (esta constitución, `AGENTS.md`, `CLAUDE.md`) antes de modificar código; inspeccionar antes de implementar.
2. Nunca asumir que una funcionalidad simulada está implementada; nunca presentar un mock como backend, IA o predicción operativos.
3. No modificar archivos fuera del alcance solicitado; sin migraciones destructivas ni cambios en secretos, permisos reales o servicios externos sin autorización.
4. Sin commits, push, merges, despliegues, cambios en Jira ni acciones de cuentas o publicación sin aprobación humana explícita.
5. Nunca inventar resultados de pruebas; informar exactamente de qué se ejecutó y qué no.
6. Documentar cada archivo modificado y su justificación.
7. Mantener coherentes `AGENTS.md`, `CLAUDE.md` y esta constitución; un cambio en uno se contrasta con los demás.

## G. Identidad del producto y aspectos legales

- Nombre y material gráfico propios. **No usar el nombre ni el logotipo de Somos F5 como marca del producto**; solo inspiración cromática. Sin material con licencia ni capturas propietarias.
- Este repositorio **no declara licencia** hasta que la Product Owner y Somos F5 aprueben una; la ausencia de licencia implica todos los derechos reservados.

## H. Documentación y política de idiomas

- La documentación del repositorio es **bilingüe español/inglés**: secciones emparejadas dentro de un archivo o un archivo canónico más una traducción claramente marcada (`NOMBRE.md` canónico + `NOMBRE.es.md`), enlazadas entre sí.
- Una única fuente canónica por regla; las traducciones nunca introducen reglas propias.
- Los identificadores de código, rutas, comandos y nombres de API no se traducen.
- La documentación distingue siempre funcionalidad implementada, simulada, pendiente y verificada.
