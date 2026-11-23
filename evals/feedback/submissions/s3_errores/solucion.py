"""Entrega sintética 3: errores de lógica en los casos normales y nombres poco claros."""


def resumen_asistencia(estados):
    if not estados:
        return {"porcentaje": None, "alerta": False}
    p = estados.count("presente")
    x = round(p * 100 / len(estados), 1)
    a = estados.count("ausente")
    return {"porcentaje": x, "alerta": a > 3}
