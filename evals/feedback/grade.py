"""Corrector del ejercicio de acceso sintético (KAN-152).

Solo para desarrollo y CI: ejecuta las entregas SINTÉTICAS de evals/feedback/submissions,
escritas por el equipo. No acepta otras rutas y nunca ejecuta código de aspirantes reales
(la corrección en sandbox, KAN-172, está fuera de alcance). Cada caso corre en un proceso
aparte, con Python aislado (-I), sin cachés (-B) y con un límite de tiempo. El resultado
se guarda en results.json para que lo use el borrador de feedback (KAN-191).

Uso, desde la raíz del repositorio:
    python evals/feedback/grade.py            # vuelve a generar results.json
    python evals/feedback/grade.py --check    # falla si results.json no está al día
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
EJERCICIO = BASE / "exercise"
ENTREGAS = BASE / "submissions"
RESULTADOS = BASE / "results.json"
LIMITE_SEGUNDOS = 2

# Se ejecuta en un proceso aparte: carga la entrega, llama a la función con un caso
# e imprime el resultado como JSON en la última línea.
RUNNER = r"""
import importlib.util, json, sys
pedido = json.load(sys.stdin)
try:
    spec = importlib.util.spec_from_file_location("entrega", pedido["ruta"])
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    funcion = modulo.resumen_asistencia
except Exception as exc:
    print(json.dumps({"estado": "no_importable", "tipo": type(exc).__name__}))
    sys.exit(0)
entrada = list(pedido["entrada"])
copia = list(entrada)
try:
    resultado = funcion(entrada)
    print(json.dumps({"estado": "ok", "resultado": resultado, "entrada_intacta": entrada == copia}))
except Exception as exc:
    print(json.dumps({"estado": "excepcion", "tipo": type(exc).__name__, "mensaje": str(exc)}))
"""


def cargar_json(ruta: Path):
    return json.loads(ruta.read_text(encoding="utf-8"))


def ejecutar_caso(solucion: Path, entrada: list) -> dict:
    pedido = json.dumps({"ruta": str(solucion), "entrada": entrada})
    try:
        proceso = subprocess.run(
            [sys.executable, "-I", "-B", "-c", RUNNER],
            input=pedido, capture_output=True, text=True, encoding="utf-8",
            timeout=LIMITE_SEGUNDOS, cwd=BASE,
        )
    except subprocess.TimeoutExpired:
        return {"estado": "tiempo_agotado"}
    lineas = proceso.stdout.strip().splitlines()
    try:
        return json.loads(lineas[-1])
    except (IndexError, json.JSONDecodeError):
        return {"estado": "salida_no_valida"}


def describir(salida: dict) -> str:
    if salida["estado"] == "ok":
        return json.dumps(salida["resultado"], ensure_ascii=False)
    return f"{salida['tipo']}: {salida['mensaje']}"


def comprobar(caso: dict, salida: dict) -> tuple[bool, str]:
    esperado = caso["esperado"]
    if salida["estado"] == "tiempo_agotado":
        return False, f"tiempo agotado ({LIMITE_SEGUNDOS} s)"
    if salida["estado"] == "salida_no_valida":
        return False, "la función no devolvió un resultado válido"
    if "error" in esperado:
        if (salida["estado"] == "excepcion" and salida["tipo"] == esperado["error"]
                and esperado["mensaje_contiene"] in salida["mensaje"]):
            return True, "ok"
        return False, (f"esperado {esperado['error']} que nombre {esperado['mensaje_contiene']!r}, "
                       f"obtenido {describir(salida)}")
    if salida["estado"] == "ok" and salida["resultado"] == esperado:
        if caso.get("comprobar_entrada_intacta") and not salida["entrada_intacta"]:
            return False, "resultado correcto, pero modifica la lista que recibe"
        return True, "ok"
    return False, f"esperado {json.dumps(esperado, ensure_ascii=False)}, obtenido {describir(salida)}"


def nivel(aprobados: int, total: int) -> int:
    if aprobados == total:
        return 3
    if aprobados * 2 >= total:
        return 2
    return 1


def corregir_entrega(carpeta: Path, rubrica: dict, casos: list) -> dict:
    salidas = {caso["id"]: ejecutar_caso(carpeta / "solucion.py", caso["entrada"]) for caso in casos}
    importable = all(salida["estado"] != "no_importable" for salida in salidas.values())

    detalle = []
    if importable:
        for caso in casos:
            aprobado, explicacion = comprobar(caso, salidas[caso["id"]])
            detalle.append({"id": caso["id"], "criterio": caso["criterio"],
                            "aprobado": aprobado, "detalle": explicacion})

    criterios, puntos, maximo = {}, 0.0, 0
    for criterio in rubrica["criterios"]:
        if criterio["medicion"] != "tests":
            criterios[criterio["id"]] = {"nivel": None, "medicion": "docente"}
            continue
        maximo += criterio["peso"]
        propios = [d for d in detalle if d["criterio"] == criterio["id"]]
        if not importable:
            criterios[criterio["id"]] = {"nivel": None, "medicion": "tests"}
            continue
        aprobados = sum(d["aprobado"] for d in propios)
        nivel_criterio = nivel(aprobados, len(propios))
        puntos += criterio["peso"] * nivel_criterio / 3
        criterios[criterio["id"]] = {"nivel": nivel_criterio, "medicion": "tests",
                                     "aprobados": aprobados, "total": len(propios)}

    return {
        "id": carpeta.name,
        "estado": "evaluada" if importable else "incompleta",
        "revision_docente_pendiente": True,
        "criterios": criterios,
        "puntos_automaticos": round(puntos, 1) if importable else None,
        "maximo_automatico": maximo,
        "casos": detalle,
    }


def generar() -> dict:
    rubrica = cargar_json(EJERCICIO / "rubric.json")
    casos = cargar_json(EJERCICIO / "cases.json")["casos"]
    carpetas = sorted(c for c in ENTREGAS.iterdir() if c.is_dir())
    return {
        "sintetico": True,
        "origen": "tests precalculados por evals/feedback/grade.py; no es una evaluación real",
        "rubrica": {"id": rubrica["id"], "version": rubrica["version"]},
        "limite_segundos_por_caso": LIMITE_SEGUNDOS,
        "entregas": [corregir_entrega(c, rubrica, casos) for c in carpetas],
    }


def serializar(datos: dict) -> str:
    return json.dumps(datos, ensure_ascii=False, indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Corrige las entregas sintéticas del ejercicio de acceso.")
    parser.add_argument("--check", action="store_true", help="falla si results.json no está al día")
    args = parser.parse_args()

    datos = generar()
    texto = serializar(datos)
    if args.check:
        if not RESULTADOS.exists() or RESULTADOS.read_text(encoding="utf-8") != texto:
            print("results.json no está al día: ejecuta python evals/feedback/grade.py", file=sys.stderr)
            return 1
        print("results.json al día")
        return 0
    RESULTADOS.write_text(texto, encoding="utf-8")
    print(f"results.json generado con {len(datos['entregas'])} entregas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
