# Asistente de documentación: consulta con cita o abstención (KAN-130 DA6, KAN-151)

`POST /api/v1/assistant/ask` responde preguntas sobre la documentación del curso con el **fragmento literal** del documento y su **cita**, o dice explícitamente que **no consta**. Nunca inventa. Solo datos sintéticos (ADR-0005).

## Contrato

Entrada: `{"question": "...", "cohort_id": "COH-IA"}`. La pregunta tiene entre 3 y 500 caracteres; `cohort_id` es opcional y limita la búsqueda a una de tus cohortes.

Salida:

| Campo | Significado |
|---|---|
| `status` | `answered` o `no_source` (abstención: no hay fuente en tu ámbito) |
| `mode` | `extractive`: el fragmento literal. El modo `generated`, redactado por un LLM, llega con T10 |
| `retrieval` | `hybrid` (palabras y significado) o `keyword` (solo palabras) |
| `answer` | «Según «título» (versión): fragmento», o «No consta en la documentación de tu curso» |
| `citations` | Documento, título, versión, vigencia y fragmento usado |
| `as_of` | Fecha de corte: la vigencia se comprueba en esta fecha (hoy, en Madrid) |
| `scope_cohorts` | Cohortes en las que se ha buscado |

## Quién puede preguntar (`app/modules/knowledge/scope.py`)

| Perfil | Documentos |
|---|---|
| Coder | Los de las cohortes de sus matrículas **activas**. Una baja no ve nada |
| Docente y coordinación | Los de las cohortes de su ámbito (permiso `knowledge.read`) |
| Administración | Todos |
| Captación, selección y aspirantes | Ninguno: `403` |

El ámbito lo decide el servidor, nunca la pregunta. Pedir una cohorte ajena con `cohort_id` devuelve `403`.

## Cómo busca (`app/modules/knowledge/retrieval.py`)

1. **Primero el ámbito.** Solo son candidatos los fragmentos de documentos del ámbito, `vigente` y dentro de su vigencia. El filtro va en la misma consulta SQL que la búsqueda.
2. **Dos búsquedas.** Por palabras, con la búsqueda de texto de PostgreSQL en español (las raíces de 4 o más letras coinciden también como prefijo), y por significado, con pgvector, si hay vector de la pregunta.
3. **Mezcla con Reciprocal Rank Fusion** (constante 60).
4. **Filtro de evidencia.** Un fragmento vale si cubre al menos el 50 % de las palabras de la pregunta, ponderadas por lo raras que son en el corpus (IDF), o si su similitud es de al menos 0,70. Si no vale ninguno, el asistente se abstiene.

Si Gemini falla, la búsqueda sigue solo por palabras. Los vectores se usan únicamente con `GISTAR_RAG_EMBED=true` y `GEMINI_API_KEY`.

## Medición con el banco de preguntas (23/11/2026)

24 preguntas (`evals/rag/questions.jsonl`), fecha de referencia 01/12/2026. Una pregunta con documento esperado acierta si ese documento es el primero; una sin documento acierta si el asistente se abstiene.

**Solo palabras** (barrido de la cobertura):

| Cobertura mínima | Aciertos | Primer documento correcto | Abstención correcta | Respuestas equivocadas | Fugas | Obsoletos |
|---|---|---|---|---|---|---|
| 0,2 | 19/24 | 14/14 | 5/10 | 5 | 0 | 0 |
| 0,4 | 17/24 | 8/14 | 9/10 | 1 | 0 | 0 |
| **0,5 (elegido)** | **17/24** | **7/14** | **10/10** | **0** | **0** | **0** |
| 0,6 | 15/24 | 5/14 | 10/10 | 0 | 0 | 0 |

**Híbrido, con vectores reales de Gemini** (cobertura 0,5, barrido de la similitud):

| Similitud mínima | Aciertos | Primer documento correcto | Abstención correcta | Respuestas equivocadas | Fugas | Obsoletos |
|---|---|---|---|---|---|---|
| 0,60 | 18/24 | 14/14 | 4/10 | 6 | 0 | 0 |
| 0,65 | 24/24 | 14/14 | 10/10 | 0 | 0 | 0 |
| **0,70 (elegido)** | **22/24** | **12/14** | **10/10** | **0** | **0** | **0** |
| 0,75 | 18/24 | 8/14 | 10/10 | 0 | 0 | 0 |

Se elige 0,70 y no 0,65 a propósito: el 24/24 se obtiene con el mismo banco que se usa para ajustar (sobreajuste), y entre 0,60 y 0,65 hay preguntas sin respuesta. 0,70 deja margen y solo cuesta dos abstenciones de más (q10 y q12). Con el ADR-0005, abstenerse es preferible a responder con un fragmento equivocado.

## Límites conocidos

- **Sinónimos en modo solo palabras.** «Fecha límite» no encuentra «Entrega»: el modo por palabras se abstiene más (7/14 respondidas). El híbrido lo cubre (12/14).
- **Sobreajuste.** Los umbrales se han ajustado con el mismo banco que los mide. KAN-188 debe añadir preguntas nuevas antes de volver a moverlos.
- **Staging.** Los vectores están activados (`GISTAR_RAG_EMBED=true`) y necesitan `GEMINI_API_KEY` en el panel de Render. Sin la clave, o si Gemini falla, el asistente busca solo por palabras.
- **Sin redacción.** La respuesta es el fragmento literal; el modo `generated` con verificación de la cita llega con T10.

## Auditoría

Cada pregunta deja una fila `assistant.ask` con el resultado (`answered`, `no_source` o `forbidden`), el modo de búsqueda, los documentos usados y, si lo hay, el código de error de Gemini. **Nunca se guarda el texto de la pregunta.**

## Repetir la medición

Desde `api/`, siempre contra una base desechable (por ejemplo, la de pruebas), porque ejecuta la ingesta:

```sh
GISTAR_DATABASE_URL=<base de pruebas> python -m app.modules.knowledge.evaluate --sweep            # solo palabras
GISTAR_DATABASE_URL=<base de pruebas> python -m app.modules.knowledge.evaluate --hybrid --sweep   # vectores reales
```

`--hybrid` solo envía a Gemini el corpus y las preguntas sintéticas, con la clave de `api/.env`. Cada pregunta se envía una vez.
