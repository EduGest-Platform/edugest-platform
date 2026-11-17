# ADR-0005 · Tecnologías del asistente de IA

**Estado:** propuesta · **Fecha:** 17/11/2026 · **Responsable:** David Rojas · **Jira:** KAN-64, KAN-94, KAN-113 (DA1)

Versión en inglés: `0005-stack-ia-asistente-en.md`.

## Contexto

La plataforma necesita un asistente que responda dos tipos de preguntas:

1. **Dudas sobre la documentación del curso** (briefs, calendarios, criterios), siempre con la cita del documento de donde sale la respuesta.
2. **Datos operativos**, por ejemplo cuántas faltas lleva una persona, siempre según los permisos de quien pregunta.

Requisitos que condicionan la decisión:

- Nunca se inventa una respuesta: si no hay fuente, se abstiene.
- Nunca muestra datos de otra cohorte ni de otra persona sin permiso.
- Solo datos sintéticos y sin coste: somos estudiantes y no hay presupuesto.
- El servidor gratuito de Render tiene 512 MB de memoria para toda la API (ADR-0008).
- Si Somos F5 quiere llevarlo a producción, cambiar de proveedor debe ser sencillo.

## Decisión

| Pieza | Elección |
|---|---|
| Almacén de vectores | PostgreSQL con pgvector (ya incluido en `infra/compose.yaml`), con índice HNSW |
| Embeddings | Gemini Embedding por API, vectores de 768, detrás de una interfaz propia |
| Búsqueda | Híbrida: por significado (pgvector) y por palabras (búsqueda de texto de PostgreSQL en español), combinadas |
| Redacción de la respuesta | Llama 3.3 70B a través de Groq, con el formato de la API de OpenAI. Si falla, respuesta extractiva: el fragmento encontrado con su cita |
| Consultas de datos | Herramientas fijas de solo lectura sobre los endpoints de Elizabeth (EL9, KAN-263), validadas con Pydantic. El modelo nunca escribe SQL |
| Orquestación | LangGraph mínimo dentro de `api/app/modules/agents/`: clasificar la pregunta, ir a documentos o a datos, comprobar la respuesta y responder |
| Evaluación | Banco de 20 a 30 preguntas en `evals/rag/` y un comando reproducible. LangSmith solo si el equipo aprueba la cuenta |

### Vigencia de la información

Los documentos del curso cambian y pueden quedar obsoletos. Para que el asistente no responda con información caducada:

- Cada documento guarda su **versión**, su **fecha de inicio de vigencia**, su **fecha de revisión o caducidad**, su **estado** (vigente u obsoleto) y una **huella del contenido** para detectar cambios.
- La búsqueda solo usa documentos vigentes.
- Cada respuesta muestra la fuente y la fecha de la versión usada (KAN-264).
- Un script diario, sin IA, marca como obsoletos los documentos caducados y avisa para revisarlos.

### Límites según quién pregunta

- El permiso se comprueba en el servidor, nunca según lo que diga el usuario.
- El filtro de cohorte y de ámbito se aplica **antes** de buscar.
- Instrucciones y herramientas separadas por tipo de usuario: una persona coder o aspirante solo ve sus propios datos y nunca puntuaciones ni rankings internos; el personal de Somos F5 puede comparar dentro de su ámbito.
- Cada pregunta deja un registro de auditoría (`audit_event`), sin guardar más datos personales de los necesarios.

### Dónde se usa IA y dónde no

La IA se usa solo donde hace falta criterio: entender una pregunta, buscar por significado y redactar. Lo que siempre da el mismo resultado se hace con scripts, por ejemplo archivar documentos o marcar los caducados. Por eso se descarta un agente «archivista».

## Alternativas descartadas

| Alternativa | Motivo |
|---|---|
| Chroma, Qdrant o FAISS | Añaden otra pieza que mantener, y el filtro de permisos quedaría fuera de PostgreSQL. `docs/01` ya excluye servicios nuevos. FAISS no guarda metadatos ni filtra por cohorte |
| Modelo de embeddings dentro de la API | Un modelo de calidad pesa entre 1 y 2 GB y no cabe en los 512 MB de Render. Uno pequeño cabe, pero busca peor |
| LLM en local (Ollama) | Lento sin tarjeta gráfica: riesgo alto en la demo |
| Gemini como LLM principal | Válido, pero Groq es más rápido; queda como alternativa por la misma interfaz |
| RAGAS para evaluar | Necesita un LLM como juez y gasta cuota. Se empieza con métricas propias |
| LangChain completo | Grande y cambia mucho entre versiones. Solo se usarían piezas concretas si hacen falta |

## Consecuencias

- **Migración 0003 (DA4, 20/11):** tablas de documentos y fragmentos con la columna de vectores de 768 y los campos de vigencia. Si un día se cambia a un modelo con otro tamaño, hará falta otra migración y reprocesar los documentos.
- **Cambiar de proveedor:** se cambia una variable de configuración y se ejecuta el comando de reindexar. Cada fragmento guarda el modelo que lo generó, porque los vectores de modelos distintos no se pueden mezclar.
- **Dependencia externa:** si la API de embeddings o la del LLM fallan, el asistente sigue funcionando con la búsqueda por palabras y la respuesta extractiva.
- **Datos:** los niveles gratuitos de Gemini y Groq son solo para la demo con datos sintéticos. Con datos reales hay que usar el nivel de pago o un servicio en Europa (RGPD), o un modelo propio en un servidor con más memoria.
- **Variables nuevas:** `GEMINI_API_KEY` y `GROQ_API_KEY` en `.env.example` y en Render (Yohanna, YO10).
- **Despliegue (sugerencia para ADR-0008):** el PostgreSQL gratuito de Render caduca a los 30 días; Neon es gratuito, tiene pgvector y no caduca. La decisión es de Yohanna.

## Métricas de evaluación

- El documento correcto aparece entre los primeros resultados.
- Fidelidad: la respuesta dice lo mismo que el fragmento citado.
- Tasa de invenciones: afirmaciones que no están en ningún fragmento.
- Abstención correcta en preguntas sin respuesta.
- Cero documentos recuperados de otra cohorte.

Se publican todas las métricas, también las malas.

## Pendiente

- Prueba de humo: indexar tres documentos sintéticos y recuperar el correcto con su cita. Se entrega en un PR aparte.
- Respuestas de Adrián a las preguntas enviadas el 17/11 (embeddings, métricas y despliegue).
- Confirmación de la PO sobre los agentes antes del 23/11 (DA7). El primero es el tutor RAG; el revisor de feedback llega con DA10.
- Comparar Gemini Embedding con un modelo local del mismo tamaño usando el banco de preguntas, antes de cerrar la decisión.
