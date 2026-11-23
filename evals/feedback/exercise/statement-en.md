# Access exercise · Workshop attendance summary

> Synthetic exercise for the EduGest demo (KAN-152). It adds extra points in preselection, but it is not exclusionary: there is no minimum score.

## Context

A fictional workshop records attendance for each session with one of these states:

| State | Meaning |
|---|---|
| `presente` | Attended |
| `retraso` | Attended, but arrived late |
| `ausente` | Did not attend |
| `pendiente` | The session has not been recorded yet |

The state values stay in Spanish because they are the values the function receives.

## What you have to do

Write a function in Python 3.12, without external libraries:

```python
def resumen_asistencia(estados: list[str]) -> dict:
    ...
```

`estados` is one person's list of states, ordered from the oldest session to the most recent one.

The function returns a dictionary with two keys:

- `porcentaje`: percentage of attended sessions (`presente` or `retraso`) over recorded sessions (all except `pendiente`), rounded to 1 decimal place. If there is no recorded session, it is `None`.
- `alerta`: `True` if there are 3 or more `ausente` among the last 6 recorded sessions (if there are fewer than 6, all of them are checked). Otherwise, `False`.

## Rules

1. The only valid states are the four in the table, in lowercase. If any other value appears, the function raises `ValueError` with a message that names the invalid value.
2. The function must not modify the list it receives.
3. The function must finish in less than 2 seconds.

## Examples

```python
resumen_asistencia(["presente", "ausente", "retraso", "ausente", "pendiente", "ausente"])
# {"porcentaje": 40.0, "alerta": True}
# 5 recorded sessions, 2 attended; 3 absences among the last recorded ones.

resumen_asistencia(["ausente", "ausente", "ausente",
                    "presente", "presente", "presente", "presente", "presente", "presente"])
# {"porcentaje": 66.7, "alerta": False}
# The 3 absences fall outside the last 6 recorded sessions.

resumen_asistencia([])
# {"porcentaje": None, "alerta": False}

resumen_asistencia(["presente", "dormido"])
# ValueError: estado no válido: 'dormido'
```

## What you submit

1. A `solucion.py` file with the `resumen_asistencia` function.
2. An `EXPLICACION.md` file of 3 to 5 lines: which decisions you made and why (for example, how you handle `pendiente` sessions). Clarity is what counts, not polished writing.

## How it is assessed

With a 4-criterion rubric worth 100 points in total: correctness (40), edge cases (25), readability (20) and explanation (15). The first two are checked with automated tests; the last two are always assessed by a member of the teaching staff.
