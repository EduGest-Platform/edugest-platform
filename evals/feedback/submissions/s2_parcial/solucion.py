"""Entrega sintética 2: funciona en los casos normales, falla en los límites."""


def resumen_asistencia(estados):
    registradas = [e for e in estados if e != "pendiente"]
    if len(registradas) == 0:
        return {"porcentaje": 0.0, "alerta": False}

    asistidas = 0
    for estado in registradas:
        if estado == "presente" or estado == "retraso":
            asistidas += 1
    porcentaje = round(asistidas / len(registradas) * 100, 1)

    ultimas = estados[-6:]
    alerta = ultimas.count("ausente") >= 3
    return {"porcentaje": porcentaje, "alerta": alerta}
