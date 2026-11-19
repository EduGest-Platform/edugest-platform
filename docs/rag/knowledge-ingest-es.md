# Ingesta de documentos del RAG (KAN-130)

Versión en inglés: [knowledge-ingest-en.md](knowledge-ingest-en.md).

Estado: implementado y probado en local con datos sintéticos (PR A). Los vectores (embeddings) y el arranque automático en el contenedor llegan en una PR posterior (PR B).

## Qué hace

Carga los documentos del curso de `evals/rag/corpus/` en las tablas `knowledge_document` y `knowledge_chunk`, para que el asistente pueda buscar en ellos filtrando por cohorte y vigencia.

Es segura y repetible:

- **Sin datos personales.** Un documento con un email, un DNI o NIE, un teléfono o el nombre completo de una persona registrada se rechaza entero. El aviso dice el tipo de dato, nunca el valor.
- **Repetible.** Cada documento guarda una huella (SHA-256) de su texto. Si nada ha cambiado, no se hace nada.
- **Nunca borra.** Un documento que sale del corpus, o que tiene una versión nueva, se marca como `obsoleto`. Así queda constancia de qué información existió.
- **Auditada.** Cada cambio real deja un evento en `audit_event`, solo con códigos e identificadores.
- **Atómica.** Una transacción por documento: si algo falla, ese documento se deshace entero.

## Cómo se ejecuta

Desde la carpeta `api/`, con la base de datos arrancada y migrada (`alembic upgrade head`):

```bash
python -m app.modules.knowledge.ingest            # ingesta real
python -m app.modules.knowledge.ingest --dry-run  # simulación: hace todo y no guarda nada
```

Opciones: `--corpus RUTA` para usar otra carpeta. Por defecto se usa `GISTAR_CORPUS_PATH`, que en local apunta a `evals/rag/corpus`.

Al terminar imprime una tabla por documento (versión, cohorte, estado, vigencia, acción, fragmentos, vector y responsable) y un resumen con el motivo de cada rechazo.

| Código de salida | Significado |
|---|---|
| 0 | Todo se ha cargado o no había cambios |
| 1 | Algún documento se ha rechazado o ha fallado; el resto sí se ha cargado |
| 2 | No se puede usar el corpus (`corpus.json` roto o ausente) o la base de datos |

## Qué le pasa a cada documento

| Acción | Cuándo |
|---|---|
| nuevo | El documento, en esa versión, no existía |
| actualizado | Ha cambiado su texto (se sustituyen sus fragmentos) o solo sus datos, como el estado o las fechas (no se vuelve a trocear) |
| sin cambios | Mismo texto y mismos datos. No se audita |
| rechazado | Datos personales, ningún contenido que indexar o una entrada incompleta en `corpus.json` |
| retirado | Ha desaparecido del corpus o tiene una versión nueva. Queda como `obsoleto` |

Una entrada de `corpus.json` mal escrita nunca retira la versión que ya estaba guardada: un error de tecleo no hace desaparecer un documento bueno.

## Cómo añadir, cambiar o retirar un documento

1. **Añadir:** crea el fichero `.md` en `evals/rag/corpus/` y añade su entrada en `corpus.json` con `id`, `file`, `title`, `cohort` (`A` o `B`), `version`, `valid_from`, `valid_until` (opcional), `status` (`vigente` u `obsoleto`), `synthetic: true` y `maintained_by`.
2. **Cambiar el texto:** edita el `.md`. Si el cambio es importante, sube también la `version` para conservar la anterior como histórico.
3. **Retirar:** pon `status: "obsoleto"` o quita la entrada. El documento no se borra.
4. Ejecuta la ingesta y revisa el informe.

`maintained_by` es el área responsable del documento, expresada como uno de los roles del sistema (`admin`, `captacion`, `seleccion`, `coordinacion` o `docente`). Nunca el nombre de una persona.

Cada cohorte del corpus se traduce a la cohorte real del seed en `app/modules/knowledge/corpus.py` (`COHORT_SCOPE`). Un test avisa si esas cohortes dejan de existir.

## Datos personales: qué detecta y sus límites

Detecta emails, DNI o NIE, teléfonos españoles y los nombres completos (dos o más palabras) de las personas registradas en la base de datos, sin distinguir mayúsculas ni tildes.

Límite: un nombre suelto o el de una persona no registrada no se detecta. Buscar nombres sueltos rechazaría documentos normales. Para producción se propone añadir un detector de entidades como Microsoft Presidio (visión futura, no implementado).

## Auditoría

| Evento | Datos guardados |
|---|---|
| `knowledge.document.created` / `updated` | documento, versión, estado y número de fragmentos |
| `knowledge.document.rejected` | documento, versión, motivo (`personal_data` o `no_content`) y tipos de dato encontrados |
| `knowledge.document.retired` | documento y versión |

Nunca se guarda el texto del documento ni el valor de un dato personal.

## Qué no hace todavía

- Los fragmentos se guardan sin vector. La búsqueda por palabras ya funciona; la semántica llega con la PR B.
- No se ejecuta sola al arrancar el contenedor (PR B).
- No hay subida de documentos desde la web. El pipeline (`pipeline.py`) no depende de dónde vengan los documentos, así que un endpoint de subida podría reutilizarlo (visión futura).
- La búsqueda, el filtro por cohorte y las respuestas con cita son la siguiente tarea (DA6, KAN-130 y KAN-151).
