"""Solución de referencia del ejercicio de acceso (KAN-152). Solo datos sintéticos."""

ASISTIDAS = {"presente", "retraso"}
VALIDOS = ASISTIDAS | {"ausente", "pendiente"}
VENTANA = 6
UMBRAL_ALERTA = 3


def resumen_asistencia(estados: list[str]) -> dict:
    for estado in estados:
        if estado not in VALIDOS:
            raise ValueError(f"estado no válido: {estado!r}")

    registradas = [estado for estado in estados if estado != "pendiente"]
    if not registradas:
        return {"porcentaje": None, "alerta": False}

    asistidas = sum(1 for estado in registradas if estado in ASISTIDAS)
    porcentaje = round(100 * asistidas / len(registradas), 1)
    alerta = registradas[-VENTANA:].count("ausente") >= UMBRAL_ALERTA
    return {"porcentaje": porcentaje, "alerta": alerta}
