"""Tests del estado de la brújula y del protocolo celular->laptop."""

import unittest
import time

from server.compass import CompassState, Orientacion, parse_mensaje


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


class TestCompassState(unittest.TestCase):
    def test_update_aplica_offset_de_calibracion(self):
        st = CompassState()
        st._offset_rumbo = 30.0  # calibración directa (Fase 5)
        st.update(Orientacion(rumbo=60.0, inclinacion=5.0, roll=0.0, ts=1000.0))
        o = st.get()
        self.assertAlmostEqual(o.rumbo, 30.0)  # 60 - 30 = 30
        self.assertEqual(o.inclinacion, 5.0)

    def test_update_envuelve_rumbo_mod_360(self):
        st = CompassState()
        st._offset_rumbo = 350.0
        st.update(Orientacion(rumbo=10.0, ts=1000.0))
        self.assertAlmostEqual(st.get().rumbo, 20.0)  # (10 - 350) mod 360 = 20

    def test_get_devuelve_copia(self):
        st = CompassState()
        st.update(Orientacion(rumbo=90.0, ts=1000.0))
        copia = st.get()
        copia.rumbo = 999.0
        self.assertEqual(st.get().rumbo, 90.0)

    def test_fresh_con_lectura_antigua(self):
        st = CompassState()
        st.update(Orientacion(rumbo=0.0, ts=time.time() - 30.0))
        self.assertFalse(st.fresh)


if __name__ == "__main__":
    unittest.main()
