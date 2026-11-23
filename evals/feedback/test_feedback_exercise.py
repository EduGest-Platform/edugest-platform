"""Pruebas del ejercicio de acceso sintético (KAN-152). Solo biblioteca estándar.

Desde la raíz del repositorio:  python -m unittest discover -s evals/feedback -v
"""

import importlib.util
import re
import tempfile
import unittest
from pathlib import Path

import grade

BASE = Path(__file__).resolve().parent
# (nivel de corrección, nivel de casos límite, puntos automáticos) calculados a mano antes del corrector
ESPERADO = {
    "s1_correcta": (3, 3, 65.0),
    "s2_parcial": (3, 1, 48.3),
    "s3_errores": (1, 1, 21.7),
    "s4_colgada": (2, 1, 35.0),
}
CASOS_COLGADOS = {"C1", "L2", "L3", "L5"}  # los casos con alguna sesión pendiente
DATOS_PERSONALES = {
    "correo": re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"),
    "DNI": re.compile(r"\b\d{8}[A-HJ-NP-TV-Z]\b"),
    "NIE": re.compile(r"\b[XYZ]\d{7}[A-HJ-NP-TV-Z]\b"),
    "teléfono": re.compile(r"(?<!\d)(?:\+34\s?)?[6789]\d{2}\s?\d{3}\s?\d{3}(?!\d)"),
}


def cargar_referencia():
    spec = importlib.util.spec_from_file_location("referencia", BASE / "reference" / "solucion.py")
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo.resumen_asistencia


class EjercicioDeAcceso(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rubrica = grade.cargar_json(grade.EJERCICIO / "rubric.json")
        cls.casos = grade.cargar_json(grade.EJERCICIO / "cases.json")["casos"]
        cls.generado = grade.generar()  # unos 10 s: la entrega colgada agota su límite 4 veces
        cls.entregas = {e["id"]: e for e in cls.generado["entregas"]}

    def test_1_la_referencia_pasa_todos_los_casos(self):
        funcion = cargar_referencia()
        for caso in self.casos:
            with self.subTest(caso=caso["id"]):
                entrada = list(caso["entrada"])
                esperado = caso["esperado"]
                if "error" in esperado:
                    with self.assertRaises(ValueError) as error:
                        funcion(entrada)
                    self.assertIn(esperado["mensaje_contiene"], str(error.exception))
                else:
                    self.assertEqual(funcion(entrada), esperado)
                    self.assertEqual(entrada, caso["entrada"], "la referencia modifica la entrada")

    def test_2_la_rubrica_es_valida(self):
        criterios = self.rubrica["criterios"]
        ids = [c["id"] for c in criterios]
        self.assertEqual(len(ids), len(set(ids)), "ids de criterio repetidos")
        self.assertTrue(all(isinstance(c["peso"], int) and c["peso"] > 0 for c in criterios))
        self.assertEqual(sum(c["peso"] for c in criterios), 100)
        self.assertIsNone(self.rubrica["nota_minima"], "el ejercicio no es excluyente")
        for c in criterios:
            with self.subTest(criterio=c["id"]):
                self.assertIn(c["medicion"], {"tests", "docente"})
                self.assertEqual(set(c["niveles"]), {"1", "2", "3"})
                self.assertTrue(all(texto.strip() for texto in c["niveles"].values()))

        medicion = {c["id"]: c["medicion"] for c in criterios}
        ids_casos = [caso["id"] for caso in self.casos]
        self.assertEqual(len(ids_casos), len(set(ids_casos)), "ids de caso repetidos")
        for caso in self.casos:
            with self.subTest(caso=caso["id"]):
                self.assertEqual(medicion.get(caso["criterio"]), "tests",
                                 "cada caso pertenece a un único criterio medido con tests")
        for criterio_id, tipo in medicion.items():
            usados = sum(caso["criterio"] == criterio_id for caso in self.casos)
            if tipo == "tests":
                self.assertGreater(usados, 0, f"{criterio_id} no tiene casos")
            else:
                self.assertEqual(usados, 0, f"{criterio_id} lo valora el docente, no un test")

    def test_3_cada_entrega_recibe_los_niveles_esperados(self):
        self.assertEqual(set(self.entregas), set(ESPERADO))
        for id_entrega, esperado in ESPERADO.items():
            with self.subTest(entrega=id_entrega):
                entrega = self.entregas[id_entrega]
                c = entrega["criterios"]
                obtenido = (c["correccion"]["nivel"], c["casos_limite"]["nivel"], entrega["puntos_automaticos"])
                self.assertEqual(obtenido, esperado)
                self.assertIsNone(c["legibilidad"]["nivel"])
                self.assertIsNone(c["explicacion"]["nivel"])
                self.assertTrue(entrega["revision_docente_pendiente"])

    def test_4_results_json_esta_al_dia(self):
        self.assertEqual(grade.RESULTADOS.read_text(encoding="utf-8"), grade.serializar(self.generado),
                         "results.json desfasado: ejecuta python evals/feedback/grade.py")

    def test_5_una_entrega_colgada_agota_el_tiempo_sin_bloquear(self):
        for caso in self.entregas["s4_colgada"]["casos"]:
            with self.subTest(caso=caso["id"]):
                if caso["id"] in CASOS_COLGADOS:
                    self.assertFalse(caso["aprobado"])
                    self.assertEqual(caso["detalle"], f"tiempo agotado ({grade.LIMITE_SEGUNDOS} s)")
                else:
                    self.assertNotIn("tiempo agotado", caso["detalle"])

    def test_5b_una_entrega_que_no_se_importa_queda_sin_nivel(self):
        with tempfile.TemporaryDirectory() as carpeta:
            Path(carpeta, "solucion.py").write_text("def resumen_asistencia(:\n", encoding="utf-8")
            entrega = grade.corregir_entrega(Path(carpeta), self.rubrica, self.casos)
        self.assertEqual((entrega["estado"], entrega["motivo"]), ("incompleta", "no_importable"))
        self.assertIsNone(entrega["puntos_automaticos"])
        self.assertTrue(all(c["nivel"] is None for c in entrega["criterios"].values()))

    def test_6_no_hay_datos_personales(self):
        propio = Path(__file__).resolve()
        archivos = [p for p in BASE.rglob("*")
                    if p.is_file() and p.suffix in {".py", ".json", ".md"} and p != propio]
        self.assertTrue(archivos)
        for archivo in archivos:
            texto = archivo.read_text(encoding="utf-8")
            for tipo, patron in DATOS_PERSONALES.items():
                with self.subTest(archivo=archivo.relative_to(BASE).as_posix(), tipo=tipo):
                    self.assertIsNone(patron.search(texto))

    def test_7_solo_se_ejecutan_las_entregas_permitidas(self):
        self.assertEqual([c.name for c in grade.carpetas_entregas()], list(grade.ENTREGAS_PERMITIDAS))
        with tempfile.TemporaryDirectory() as carpeta:
            for nombre in grade.ENTREGAS_PERMITIDAS:
                Path(carpeta, nombre).mkdir()
            Path(carpeta, "intrusa").mkdir()
            with self.assertRaisesRegex(ValueError, "intrusa"):
                grade.carpetas_entregas(Path(carpeta))
            Path(carpeta, "intrusa").rmdir()
            Path(carpeta, grade.ENTREGAS_PERMITIDAS[0]).rmdir()
            with self.assertRaisesRegex(ValueError, grade.ENTREGAS_PERMITIDAS[0]):
                grade.carpetas_entregas(Path(carpeta))

    def test_8_una_terminacion_inesperada_no_se_puntua(self):
        codigos = {
            "os._exit": "import os\n\n\ndef resumen_asistencia(estados):\n    os._exit(3)\n",
            "sys.exit": "import sys\n\n\ndef resumen_asistencia(estados):\n    sys.exit(0)\n",
        }
        for nombre, codigo in codigos.items():
            with self.subTest(salida=nombre), tempfile.TemporaryDirectory() as carpeta:
                Path(carpeta, "solucion.py").write_text(codigo, encoding="utf-8")
                entrega = grade.corregir_entrega(Path(carpeta), self.rubrica, self.casos)
                self.assertEqual((entrega["estado"], entrega["motivo"]), ("incompleta", "error_de_ejecucion"))
                self.assertIsNone(entrega["puntos_automaticos"])
                self.assertTrue(all(c["nivel"] is None for c in entrega["criterios"].values()))
                self.assertTrue(all(c["aprobado"] is None and "inesperada" in c["detalle"]
                                    for c in entrega["casos"]))

    def test_9_una_entrega_sin_la_funcion_queda_sin_nivel(self):
        with tempfile.TemporaryDirectory() as carpeta:
            Path(carpeta, "solucion.py").write_text("def otra_funcion():\n    return None\n", encoding="utf-8")
            entrega = grade.corregir_entrega(Path(carpeta), self.rubrica, self.casos)
        self.assertEqual((entrega["estado"], entrega["motivo"]), ("incompleta", "no_importable"))
        self.assertEqual(entrega["casos"], [])

    def test_10_un_caso_que_no_termina_agota_el_tiempo(self):
        with tempfile.TemporaryDirectory() as carpeta:
            solucion = Path(carpeta, "solucion.py")
            solucion.write_text("def resumen_asistencia(estados):\n    while True:\n        pass\n", encoding="utf-8")
            self.assertEqual(grade.ejecutar_caso(solucion, ["presente"]), {"estado": "tiempo_agotado"})


if __name__ == "__main__":
    unittest.main()
