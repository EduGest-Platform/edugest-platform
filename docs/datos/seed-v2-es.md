# Seed v2: datos sintéticos de demostración (KAN-173)

Versión en inglés: [seed-v2-en.md](seed-v2-en.md).

Estado: implementado y probado en local. Todos los datos son sintéticos.

## Qué añade

1. **100 candidaturas enviadas** en `src/gistar/seed.json` (antes había 12). Las 88 nuevas se generan con una semilla fija (173), así que el resultado es siempre el mismo. Solo usan correos `@example.test`.
2. **Datos académicos** en la API, derivados de `seed.json` con las mismas reglas que el prototipo web (`src/gistar/migrate.ts`):
   - Un árbol de competencias publicado por programa (P-IA y P-DATA), asignado a su cohorte.
   - Evaluaciones de competencias: la del sprint y el nivel actual que figura en `seed.json`.
   - Sesiones con fecha y registros de asistencia de cada coder.

`seed.json` sigue siendo la única fuente: la web y la API leen los mismos datos.

## Cómo se ejecuta

Desde `api/`, con la base de datos arrancada y migrada (`alembic upgrade head`):

```bash
python -m app.seed
```

- Si la base está vacía, carga los datos base y después los académicos.
- Si los datos base ya existen, solo carga los académicos.
- Si los datos académicos ya existen (hay algún árbol de competencias), no hace nada. Por eso se puede ejecutar todas las veces que haga falta, y staging recibe los datos sin borrar la base.

Para regenerar las candidaturas de `seed.json` (solo si cambian las reglas del generador):

```bash
python -m scripts.seed_v2_candidates
```

Rehace las candidaturas generadas (marcadas con `origen: "sintetico_seed_v2"`) y conserva las escritas a mano.

## Reglas de los datos académicos

| Dato | Regla |
|---|---|
| Evaluación del sprint | COH-IA el 20/10/2026 (IA-01, IA-03, IA-07) y COH-DATA el 27/10/2026 (DAT-02, DAT-03, DAT-07). Nivel: uno menos que el actual, con un mínimo de 1 |
| Sin evaluación de sprint | E-019 (no entregó) y E-002, E-006, E-013, E-017 (entrega sin revisar) |
| Nivel actual | El de `seed.json`, con fecha 30/10/2026. Niveles de 1 a 3 |
| Sesiones | COH-IA: lunes y jueves de 9:30 a 13:30. COH-DATA: martes y viernes de 15:30 a 19:30. Sin festivos (12/10, 1/11 y 8/12) |
| Asistencia | Media jornada por sesión (0,5). Los presentes y ausentes de cada coder coinciden con su `asistencias_resumen` |
| Ausencias | Cada ausencia es justificada o injustificada. La probabilidad de injustificada crece con el riesgo latente, con los mismos parámetros que el modelo de abandono (`ml/dropout/data.py`) |

Cada registro de asistencia guarda su primera versión en el historial de correcciones, igual que uno creado desde la API.

## Pruebas

- `api/tests/test_seed_academic.py`: al menos 100 candidaturas con correos sintéticos, árboles publicados y asignados, niveles iguales a `seed.json`, asistencia que cuadra con el resumen, carga repetible y resultado reproducible con la misma semilla.
- `api/tests/test_rbac.py` y `api/tests/test_applications.py` calculan los números esperados a partir de los datos sembrados, en lugar de usar números fijos. Así no se rompen cuando cambia `seed.json`.

## Qué no hace todavía

- No genera entregas de proyectos. Dependen del modelo de entregas (KAN-56).
- No cambia los datos base (personas, convocatorias, cohortes y usuarios).
