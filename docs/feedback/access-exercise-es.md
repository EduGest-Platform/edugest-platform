# Ejercicio de acceso sintético con rúbrica y corrección por tests (KAN-152)

Base de la demo de feedback automatizado (KAN-67). Todo es **sintético**: el enunciado, las entregas y los resultados los ha escrito el equipo. No es una evaluación real ni valida nada sobre personas.

## Qué hay y dónde

| Ruta | Contenido |
|---|---|
| `evals/feedback/exercise/statement-es.md`, `statement-en.md` | Enunciado para la persona aspirante: función `resumen_asistencia(estados)` |
| `evals/feedback/exercise/rubric.json` | Rúbrica de 4 criterios, pesos, niveles 1–3 y regla de niveles |
| `evals/feedback/exercise/cases.json` | 10 casos de prueba; cada uno pertenece a un solo criterio |
| `evals/feedback/reference/solucion.py` | Solución de referencia |
| `evals/feedback/submissions/` | 4 entregas sintéticas con fallos conocidos: correcta, parcial, con errores y colgada |
| `evals/feedback/grade.py` | Corrector |
| `evals/feedback/results.json` | Resultados precalculados que usará el borrador de feedback (KAN-191) |
| `evals/feedback/test_feedback_exercise.py` | Pruebas; se ejecutan en el job `feedback` de la CI |

## Rúbrica

| Criterio | Peso | Cómo se mide |
|---|---|---|
| Corrección funcional | 40 | 5 casos de prueba |
| Casos límite y validación de entrada | 25 | 5 casos de prueba |
| Legibilidad y estructura | 20 | Siempre el docente |
| Explicación de las decisiones | 15 | Siempre el docente, sobre `EXPLICACION.md` |

- **Niveles por tests:** 3 si pasa todos los casos del criterio; 2 si pasa al menos la mitad; 1 si pasa menos. Si la entrega no se puede importar, el criterio queda **sin nivel** y la entrega, **incompleta**: nunca hay nivel 0.
- **Puntos:** suma de `peso × nivel / 3`, sobre 100. El corrector solo calcula los 65 puntos de los criterios medidos con tests; legibilidad y explicación quedan sin nivel y con la revisión del docente pendiente.
- **No es excluyente:** `nota_minima` es `null`. El ejercicio suma puntos extra en la preselección.
- `competencias` está vacío a propósito: las competencias C1–C10 son de coders matriculados, no de aspirantes.

## Resultados de las entregas sintéticas

| Entrega | Corrección | Casos límite | Puntos automáticos (de 65) |
|---|---|---|---|
| `s1_correcta` | 3 | 3 | 65,0 |
| `s2_parcial` | 3 | 1 | 48,3 |
| `s3_errores` | 1 | 1 | 21,7 |
| `s4_colgada` | 2 | 1 | 35,0 |

## Cómo se ejecuta

Desde la raíz del repositorio, con Python 3.12 y sin dependencias:

```sh
python evals/feedback/grade.py                   # vuelve a generar results.json (unos 10 s)
python evals/feedback/grade.py --check           # falla si results.json no está al día
python -m unittest discover -s evals/feedback -v # las pruebas, igual que la CI
```

Si cambias el enunciado, la rúbrica, los casos o una entrega, vuelve a generar `results.json` y súbelo en el mismo commit: la prueba 4 falla si está desfasado.

## Garantías y límites

- **Nunca ejecuta código de aspirantes reales.** El corrector solo acepta las carpetas de `evals/feedback/submissions/`, escritas por el equipo. La corrección en un sandbox aislado (KAN-172) está fuera de alcance.
- Cada caso corre en un proceso aparte, con Python aislado (`-I`), sin cachés (`-B`) y con un límite de 2 segundos. Un caso que se cuelga cuenta como fallado y no bloquea el resto.
- `results.json` es determinista: no guarda fechas, tiempos ni rutas locales.
- La prueba 6 comprueba que no hay correos, DNI, NIE ni teléfonos en `evals/feedback`.
- Los criterios del docente nunca los decide un test ni la IA. El borrador de KAN-191 solo podrá sugerirlos, y nada se publica sin revisión (KAN-67).

## Qué usa KAN-191

Por cada entrega: `criterios` (nivel, aprobados y total por criterio), `puntos_automaticos`, `revision_docente_pendiente` y `casos` (id, criterio, aprobado y un `detalle` legible, por ejemplo `esperado {...}, obtenido {...}` o `tiempo agotado (2 s)`). Más la `rubrica` con su id y versión, para registrar con qué versión se generó el borrador.
