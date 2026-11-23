"""Entrega sintética 4: bucle infinito cuando aparece una sesión pendiente."""

VALIDOS = ("presente", "retraso", "ausente", "pendiente")


def resumen_asistencia(estados):
    for estado in estados:
        if estado not in VALIDOS:
            raise ValueError(f"estado no válido: {estado!r}")

    registradas = []
    i = 0
    while i < len(estados):
        if estados[i] == "pendiente":
            continue
        registradas.append(estados[i])
        i += 1

    if not registradas:
        return {"porcentaje": None, "alerta": False}
    asistidas = len([e for e in registradas if e in ("presente", "retraso")])
    porcentaje = round(100 * asistidas / len(registradas), 1)
    return {"porcentaje": porcentaje, "alerta": registradas[-6:].count("ausente") >= 3}
