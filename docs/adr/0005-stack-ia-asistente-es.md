# ADR-0005 · Tecnologías del asistente de IA

**Estado:** propuesta · **Fecha:** 18/11/2026 (primera versión: 17/11/2026) · **Responsable:** David Rojas · **Jira:** KAN-64, KAN-94, KAN-113 (DA1)

Versión en inglés: `0005-stack-ia-asistente-en.md`.

## Contexto

La plataforma necesita un asistente que responda dos tipos de preguntas:

1. **Dudas sobre la documentación del curso** (briefs, calendarios, criterios), siempre con la cita del documento de donde sale la respuesta.
2. **Datos operativos**, por ejemplo el porcentaje de una cohorte que tiene una competencia, siempre según los permisos de quien pregunta.

Requisitos que condicionan la decisión:

- Nunca se inventa una respuesta: si no hay fuente, se abstiene.
- Nunca muestra datos de otra cohorte ni de otra persona sin permiso.
- Solo datos sintéticos y sin coste: somos estudiantes y no hay presupuesto.
- El plan gratuito de Render da a la API 512 MB de memoria y 0,1 CPU (documentación oficial de Render, recogida en `docs/deploy/KAN-142-render-feasibility.md`).
- El briefing pide LangChain/LangGraph para orquestar el sistema RAG y los flujos del agente, y LangSmith para la trazabilidad.
- Si Somos F5 quiere llevarlo a producción, cambiar de proveedor debe ser sencillo.

## Decisión

| Pieza | Elección |
|---|---|
| Almacén de vectores | PostgreSQL con pgvector (imagen `pgvector/pgvector:pg16`, ya en `infra/compose.yaml`). Distancia coseno (`<=>`). Búsqueda exacta, sin índice aproximado, mientras el corpus sea pequeño |
| Embeddings | `gemini-embedding-001` por API, vectores de 768 normalizados antes de guardarlos, detrás de una interfaz propia |
| Búsqueda | Híbrida: por significado (pgvector) y por palabras (búsqueda de texto de PostgreSQL en español), combinadas |
| Redacción de la respuesta | Llama 3.3 70B a través de Groq, con el formato de la API de OpenAI. Si falla, respuesta extractiva: el fragmento encontrado con su cita. Cada respuesta indica su modo: `generated` o `extractive` |
| Consultas de datos | Herramientas fijas de solo lectura sobre los endpoints de Elizabeth (EL9, KAN-263), validadas con Pydantic. El modelo nunca escribe SQL |
| Orquestación | LangGraph mínimo con pasos fijos dentro de `api/app/modules/agents/`: clasificar la pregunta, ir a documentos o a datos, comprobar la cita y responder |
| Evaluación | Banco de preguntas en `evals/rag/` (PR #14) y un comando reproducible. LangSmith solo si el equipo aprueba la cuenta |

### Qué significa «agente» en este ADR

- Un flujo con pasos fijos que solo decide a qué fuente ir. No actúa por su cuenta, no escribe en la base de datos y no envía nada a nadie.
- Lo que el asistente redacte para otra persona, por ejemplo un borrador de feedback (DA10), lo revisa y lo aprueba siempre una persona.
- Esto modifica el punto 5 de `docs/01-gap-to-be.md`, que decía «No hacer: … agentes». Pasa a decir «agentes autónomos que actúan sin revisión humana». Motivo: el briefing pide LangGraph para orquestar el RAG y los flujos del agente. El cambio va en este mismo PR y necesita la confirmación de la PO.

### Búsqueda y filtro de permisos

- El filtro de cohorte, de ámbito y de vigencia va en la misma consulta SQL que la búsqueda.
- Con un índice aproximado (HNSW), pgvector aplica ese filtro después de recorrer el índice, y puede devolver menos resultados de los pedidos o ninguno. Por eso empezamos con búsqueda exacta: con unos cientos de fragmentos tarda milisegundos y el filtro siempre es exacto.
- Si el corpus crece, se añade HNSW (`vector_cosine_ops`) con `hnsw.iterative_scan` (pgvector 0.8 o superior) y se vuelve a pasar el banco de preguntas.

### Vigencia de la información

Los documentos del curso cambian y pueden quedar obsoletos. Para que el asistente no responda con información caducada:

- Cada documento guarda su **versión**, su **fecha de inicio de vigencia**, su **fecha de revisión o caducidad**, su **estado** (vigente u obsoleto) y una **huella del contenido** para detectar cambios.
- La búsqueda solo usa documentos vigentes.
- Cada respuesta muestra la fuente y la fecha de la versión usada (KAN-264).
- Un script diario, sin IA, marca como obsoletos los documentos caducados y avisa para revisarlos.

### Límites según quién pregunta

Roles reales del código (`api/app/core/authz.py`):

| Rol | Documentos | Datos |
|---|---|---|
| `admin` | Todos | Herramientas de solo lectura, ámbito global |
| `docente` | Los de su cohorte | Los de su cohorte, cuando existan los permisos académicos de F3 |
| `coordinacion` | Los de su ámbito | Solo agregados (porcentajes y totales), nunca nombres |
| `captacion`, `seleccion` | Los del proceso de selección de su convocatoria | Ninguno en la primera versión |
| `coder` (todavía no existe; llega con F3) | Los de su cohorte | Solo los suyos; nunca puntuaciones internas ni rankings |
| Aspirante | Fuera de la primera versión | Fuera de la primera versión |

- Prioridad: primero el personal (docencia y coordinación). El alumnado usa el mismo motor con su propio filtro, porque el briefing pide un asistente para el alumnado.
- El permiso se comprueba en el servidor, nunca según lo que diga el usuario.
- Cada pregunta deja un registro en `audit_event`, la tabla de auditoría que ya existe desde F1. No se guarda el texto de la pregunta: solo la ruta (documentos o datos), los documentos usados, el resultado (respondida, sin fuente o rechazada por permisos) y el modo de la respuesta.

### Dónde se usa IA y dónde no

La IA se usa solo donde hace falta criterio: entender una pregunta, buscar por significado y redactar. Lo que siempre da el mismo resultado se hace con scripts, por ejemplo archivar documentos o marcar los caducados. Por eso se descarta un agente «archivista».

## Alternativas descartadas

| Alternativa | Motivo |
|---|---|
| Chroma, Qdrant o FAISS | Añaden otra pieza que mantener, y el filtro de permisos quedaría fuera de PostgreSQL. `docs/01` ya excluye Qdrant y Chroma. FAISS no guarda metadatos ni filtra por cohorte |
| Modelo de embeddings dentro de la API | Un modelo de calidad pesa entre 1 y 2 GB y no cabe en los 512 MB de Render. Uno pequeño cabe, pero busca peor |
| LLM en local (Ollama) | Lento sin tarjeta gráfica: riesgo alto en la demo |
| Gemini como LLM principal | Válido, pero Groq es más rápido; queda como alternativa por la misma interfaz |
| RAGAS para evaluar | Necesita un LLM como juez y gasta cuota. Se empieza con métricas propias |
| LangChain completo | Grande y cambia mucho entre versiones. Solo se usarían piezas concretas si hacen falta |

## Consecuencias

- **Migración 0003 (DA4, 20/11):** tablas de documentos y fragmentos con una columna `vector(768)`, los campos de vigencia y el modelo que generó cada vector. Sin índice HNSW al principio. Si un día se cambia a un modelo con otro tamaño, hará falta otra migración y reprocesar los documentos.
- **Cambiar de proveedor:** se cambia una variable de configuración y se ejecuta el comando de reindexar. Cada fragmento guarda el modelo que lo generó, porque los vectores de modelos distintos no se pueden mezclar.
- **Dependencia externa:** si la API de embeddings o la del LLM fallan, el asistente sigue funcionando con la búsqueda por palabras y la respuesta extractiva.
- **Privacidad:** a Gemini y a Groq no solo viajan los documentos, también las preguntas. Los términos del nivel gratuito de la API de Gemini dicen que Google usa ese contenido para mejorar sus productos y piden no enviar información personal. Por eso está prohibido conectarlo a datos reales, también en una demo con Somos F5. Con datos reales hay que usar el nivel de pago, un servicio en Europa (RGPD) o un modelo propio.
- **Variables nuevas:** `GEMINI_API_KEY` y `GROQ_API_KEY` en `.env.example` y en `render.yaml` con `sync: false` (Yohanna, YO10).
- **Despliegue:** la base de datos de Render no admite conexiones desde internet (ADR-0008). Por eso la carga de documentos se ejecuta dentro del servicio de la API y se puede repetir sin coste: si la huella de un documento no cambia, no se vuelve a procesar. La caducidad de 30 días de la base gratuita ya está en ADR-0008: creada a partir del 11/11, dura hasta después de la defensa.

## Métricas de evaluación

- El documento correcto aparece entre los primeros resultados (Recall@3).
- Fidelidad: la respuesta dice lo mismo que el fragmento citado.
- Tasa de invenciones: afirmaciones que no están en ningún fragmento.
- Abstención correcta en preguntas sin respuesta.
- Cero documentos recuperados de otra cohorte.

Se publican todas las métricas, también las malas.

## Pendiente

- **Confirmación de la PO** antes del 23/11 (DA7): el cambio del punto 5 de `docs/01` y los agentes. El primero es el tutor RAG; el revisor de feedback llega con DA10.
- **Respuestas de Adrián** a las preguntas del 17/11 (embeddings, métricas y despliegue). Si cambian algo, se actualiza este ADR.
- **Comparar** Gemini Embedding con un modelo local de 768 dimensiones usando el banco de preguntas, antes del 2/12 (evaluación, KAN-188). Criterio: si Gemini no supera al modelo local en al menos 5 puntos de Recall@3, se elige el local, siempre que quepa en la memoria del servidor.
- **Evidencia ya entregada:** prueba de humo en la PR #13 y banco de preguntas en la PR #14.
