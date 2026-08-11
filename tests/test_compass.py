"""Tests del estado de la brújula y del protocolo celular->laptop."""

import tempfile
import unittest
import time
from pathlib import Path

from server.compass import Calibracion, CompassState, Orientacion, parse_mensaje


class TestParseMensaje(unittest.TestCase):
    def test_mensaje_valido(self):
        datos = {"tipo": "orientacion", "rumbo": 212.3, "inclinacion": 8.5,
                 "roll": 0.0, "ts": 1720000000.123}
        o = parse_mensaje(datos)
        self.assertIsNotNone(o)
        self.assertEqual(o.rumbo, 212.3)
        self.assertEqual(o.inclinacion, 8.5)
        self.assertEqual(o.roll, 0.0)

    def test_tipo_incorrecto(self):
        self.assertIsNone(parse_mensaje({"tipo": "otro", "rumbo": 10.0}))

    def test_campos_faltantes(self):
        self.assertIsNone(parse_mensaje({"tipo": "orientacion", "rumbo": 10.0}))

    def test_valores_fuera_de_rango(self):
        base = {"tipo": "orientacion", "inclinacion": 0.0, "roll": 0.0,
                "ts": 1720000000.123}
        mal = dict(base, rumbo=360.0)
        self.assertIsNone(parse_mensaje(mal))
        mal = dict(base, rumbo=-1.0)
        self.assertIsNone(parse_mensaje(mal))
        mal = dict(base, rumbo=10.0, inclinacion=95.0)
        self.assertIsNone(parse_mensaje(mal))
        mal = dict(base, rumbo=10.0, roll=200.0)
        self.assertIsNone(parse_mensaje(mal))

    def test_ts_invalido(self):
        datos = {"tipo": "orientacion", "rumbo": 10.0, "inclinacion": 0.0,
                 "roll": 0.0, "ts": 0}
        self.assertIsNone(parse_mensaje(datos))

    def test_no_dict(self):
        self.assertIsNone(parse_mensaje([1, 2, 3]))
        self.assertIsNone(parse_mensaje(None))

    def test_mensaje_calibrar(self):
        c = parse_mensaje({"tipo": "calibrar", "rumbo": 5.3})
        self.assertIsInstance(c, Calibracion)
        self.assertEqual(c.rumbo, 5.3)

    def test_calibrar_invalido(self):
        self.assertIsNone(parse_mensaje({"tipo": "calibrar", "rumbo": 360.0}))
        self.assertIsNone(parse_mensaje({"tipo": "calibrar", "rumbo": -1.0}))
        self.assertIsNone(parse_mensaje({"tipo": "calibrar"}))
        self.assertIsNone(parse_mensaje({"tipo": "calibrar", "rumbo": "x"}))


class TestCompassState(unittest.TestCase):
    def setUp(self):
        self.st = CompassState(ruta_calibracion=None)

    def test_update_aplica_offset_de_calibracion(self):
        self.st._offset_rumbo = 30.0  # calibración directa (Fase 5)
        self.st.update(Orientacion(rumbo=60.0, inclinacion=5.0, roll=0.0, ts=1000.0))
        o = self.st.get()
        self.assertAlmostEqual(o.rumbo, 30.0)  # 60 - 30 = 30
        self.assertEqual(o.inclinacion, 5.0)

    def test_update_envuelve_rumbo_mod_360(self):
        self.st._offset_rumbo = 350.0
        self.st.update(Orientacion(rumbo=10.0, ts=1000.0))
        self.assertAlmostEqual(self.st.get().rumbo, 20.0)  # (10 - 350) mod 360 = 20

    def test_get_devuelve_copia(self):
        self.st.update(Orientacion(rumbo=90.0, ts=1000.0))
        copia = self.st.get()
        copia.rumbo = 999.0
        self.assertEqual(self.st.get().rumbo, 90.0)

    def test_fresh_mide_la_recepcion_no_el_ts_del_celular(self):
        # Aunque el celular mande un ts viejo (reloj sin sincronizar), si la
        # lectura se recibió ahora, es fresh.
        self.st.update(Orientacion(rumbo=0.0, ts=time.time() - 30.0))
        self.assertTrue(self.st.fresh)
        # Simula que no llegan datos hace rato: fresh se vuelve falso.
        self.st._ultima_lectura = time.time() - 30.0
        self.assertFalse(self.st.fresh)

    def test_calibrar_hace_cero_el_rumbo_actual(self):
        self.st.update(Orientacion(rumbo=50.0, ts=1000.0))
        offset = self.st.calibrar(50.0)
        self.assertAlmostEqual(offset, 50.0)
        self.assertAlmostEqual(self.st.get().rumbo, 0.0)
        self.assertTrue(self.st.calibrado)
        # la siguiente lectura ya viene corregida
        self.st.update(Orientacion(rumbo=60.0, ts=1001.0))
        self.assertAlmostEqual(self.st.get().rumbo, 10.0)

    def test_calibrar_vuelve_a_aplicar_ultima_lectura(self):
        self.st.update(Orientacion(rumbo=80.0, ts=1000.0))
        self.st.calibrar(10.0)  # el norte está a 10° del celular
        self.assertAlmostEqual(self.st.get().rumbo, 70.0)  # 80 - 10

    def test_sin_calibrar_no_marca_calibrado(self):
        self.assertFalse(self.st.calibrado)

    def test_offset_se_persiste_y_se_carga(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "calibracion.json"
            a = CompassState(ruta_calibracion=ruta)
            a.calibrar(123.4)
            self.assertTrue(ruta.exists())
            b = CompassState(ruta_calibracion=ruta)
            self.assertTrue(b.calibrado)
            b.update(Orientacion(rumbo=123.4, ts=1000.0))
            self.assertAlmostEqual(b.get().rumbo, 0.0)


if __name__ == "__main__":
    unittest.main()
