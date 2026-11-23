"""Entrega sintética 1: correcta, escrita de otra forma que la referencia."""

ESTADOS_ASISTIDOS = ("presente", "retraso")
ESTADOS_VALIDOS = ("presente", "retraso", "ausente", "pendiente")


def resumen_asistencia(estados):
    sesiones_registradas = []
    for estado in estados:
        if estado not in ESTADOS_VALIDOS:
            raise ValueError(f"estado no válido: {estado!r}")
        if estado != "pendiente":
            sesiones_registradas.append(estado)

    if len(sesiones_registradas) == 0:
        return {"porcentaje": None, "alerta": False}

    total_asistidas = len([e for e in sesiones_registradas if e in ESTADOS_ASISTIDOS])
    porcentaje = round(total_asistidas * 100 / len(sesiones_registradas), 1)

    ultimas_seis = sesiones_registradas[-6:]
    ausencias_recientes = ultimas_seis.count("ausente")
    return {"porcentaje": porcentaje, "alerta": ausencias_recientes >= 3}
