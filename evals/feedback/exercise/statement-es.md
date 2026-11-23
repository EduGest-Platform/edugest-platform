# Ejercicio de acceso · Resumen de asistencia de un taller

> Ejercicio sintético para la demo de EduGest (KAN-152). Suma puntos extra en la preselección, pero no es excluyente: no tiene nota mínima.

## Contexto

Un taller ficticio registra la asistencia de cada sesión con uno de estos estados:

| Estado | Significado |
|---|---|
| `presente` | Asistió |
| `retraso` | Asistió, pero llegó tarde |
| `ausente` | No asistió |
| `pendiente` | La sesión todavía no se ha registrado |

## Qué tienes que hacer

Escribe en Python 3.12, sin librerías externas, una función:

```python
def resumen_asistencia(estados: list[str]) -> dict:
    ...
```

`estados` es la lista de estados de una persona, ordenada de la sesión más antigua a la más reciente.

La función devuelve un diccionario con dos claves:

- `porcentaje`: porcentaje de sesiones asistidas (`presente` o `retraso`) sobre las sesiones registradas (todas menos `pendiente`), redondeado a 1 decimal. Si no hay ninguna sesión registrada, vale `None`.
- `alerta`: `True` si hay 3 o más `ausente` entre las 6 últimas sesiones registradas (si hay menos de 6, se miran todas las que haya). En otro caso, `False`.

## Reglas

1. Los estados válidos son solo los cuatro de la tabla, en minúsculas. Si aparece otro valor, la función lanza `ValueError` con un mensaje que diga cuál es el valor no válido.
2. La función no debe modificar la lista que recibe.
3. La función debe terminar en menos de 2 segundos.

## Ejemplos

```python
resumen_asistencia(["presente", "ausente", "retraso", "ausente", "pendiente", "ausente"])
# {"porcentaje": 40.0, "alerta": True}
# 5 sesiones registradas, 2 asistidas; 3 ausencias entre las últimas registradas.

resumen_asistencia(["ausente", "ausente", "ausente",
                    "presente", "presente", "presente", "presente", "presente", "presente"])
# {"porcentaje": 66.7, "alerta": False}
# Las 3 ausencias quedan fuera de las 6 últimas sesiones registradas.

resumen_asistencia([])
# {"porcentaje": None, "alerta": False}

resumen_asistencia(["presente", "dormido"])
# ValueError: estado no válido: 'dormido'
```

## Qué entregas

1. Un archivo `solucion.py` con la función `resumen_asistencia`.
2. Un archivo `EXPLICACION.md` de 3 a 5 líneas: qué decisiones has tomado y por qué (por ejemplo, cómo tratas las sesiones `pendiente`). Se valora que sea claro, no que esté bien redactado.

## Cómo se valora

Con una rúbrica de 4 criterios que suman 100 puntos: corrección (40), casos límite (25), legibilidad (20) y explicación (15). Los dos primeros se comprueban con tests automáticos; los dos últimos los valora siempre una persona del equipo docente.
