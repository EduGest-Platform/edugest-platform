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
- Si los datos base ya existen, no los toca y solo completa los académicos.
- Los datos académicos se completan pieza a pieza: solo se crea lo que falta y nunca se modifica lo que ya existe. Un árbol en borrador, una sesión o una evaluación creados desde la API se conservan tal cual, y no hacen fallar el arranque. Volver a ejecutarlo no crea nada.

**Staging (una base que ya existe):** recibe solo los datos académicos. **No recibe las 88 candidaturas generadas**, porque los datos base no se vuelven a cargar. Para tenerlas haría falta `python -m app.seed --reset`, que borra toda la base: no se hace en staging sin acuerdo del equipo.

### Cómo se completa una base que ya tiene datos

| Pieza | Si ya existe algo |
|---|---|
| Árbol de competencias | Si el programa ya tiene una versión publicada, se usa esa. Si solo hay borradores o versiones archivadas, se publica la del seed con el número de versión siguiente, y el borrador no se toca |
| Asignación a la cohorte | Solo se asignan las cohortes que no tienen árbol |
| Evaluaciones | Se buscan por código de competencia en el árbol asignado a la cohorte. No se añade nada a un coder que ya tenga una evaluación de esa competencia |
| Sesiones | Si ya hay una sesión en esa fecha y turno, se reutiliza. Si ese día ya tiene una sesión que se solapa (un día completo frente a una mañana o una tarde), el seed no crea la suya: es la misma regla que aplica la API |
| Registros de asistencia | No se crea el de un coder que ya tenga registro en esa sesión. Por eso, si alguien registró asistencia a mano, los totales pueden no coincidir exactamente con `asistencias_resumen` |

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

- `api/tests/test_seed_academic.py`: al menos 100 candidaturas con correos sintéticos, árboles publicados y asignados, niveles iguales a `seed.json`, asistencia que cuadra con el resumen, carga repetible, resultado reproducible con la misma semilla y bases con datos creados desde la API (un árbol en borrador y una sesión con un registro manual).
- `api/tests/test_rbac.py` y `api/tests/test_applications.py` calculan los números esperados a partir de los datos sembrados, en lugar de usar números fijos. Así no se rompen cuando cambia `seed.json`.

## Qué no hace todavía

- Entregas (KAN-56): una actividad por tarea de `seed.json` en cada cohorte de su programa, con plazo a las 23:59 hora local. «enviada» se entrega el día anterior al plazo y «fuera_de_plazo» dos días después. Los borradores y E-019 no tienen entrega (salen como pendiente o vencida). E-002, E-006, E-013 y E-017 quedan entregadas sin revisar. `check_results` son resultados de tests sintéticos ya calculados: la plataforma nunca ejecuta código.
- No cambia los datos base (personas, convocatorias, cohortes y usuarios).
