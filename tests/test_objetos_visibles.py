"""Tests de la lista de objetos visibles (tecla o): estrellas con nombre
propio, planetas/Luna y constelaciones que caen dentro del encuadre, con su
az/alt para apuntar la cámara.

Requieren el catálogo BSC (`data/catalogo/bsc5.dat`) y las efemérides
(`data/models/de421.bsp`); se descargan con `tools/download_models.py`.
"""

import unittest
from datetime import datetime, timezone

import numpy as np
from skyfield.api import load

from src.skyrender.astro import RUTA_EFEMERIDES, Ubicacion, altaz_con_skyfield
from src.skyrender.catalogo import RUTA_CATALOGO
from src.skyrender.render import SkyRenderer

_LAT, _LON = 10.0, -68.0
_FECHA = datetime(2026, 1, 15, 2, 0, 0, tzinfo=timezone.utc)
# Sirio (Alp CMa): RA/Dec J2000 en grados.
_SIRIO = (101.287, -16.7161)


def _t():
    return load.timescale().from_datetime(_FECHA)


@unittest.skipUnless(RUTA_CATALOGO.exists(), "Falta el catálogo BSC")
class TestObjetosVisibles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.renderer = SkyRenderer(
            ubicacion=Ubicacion(lat=_LAT, lon=_LON, nombre="test"),
            ancho=1280, alto=720, fov_deg=60.0)

    def _az_alt_sirio(self):
        alt, az = altaz_con_skyfield(np.array([_SIRIO[0]]),
                                     np.array([_SIRIO[1]]),
                                     _LAT, _LON, _t())
        return float(az[0]), float(alt[0])

    @unittest.skipUnless(RUTA_EFEMERIDES.exists(),
                         "Faltan las efemérides de421.bsp (referencia)")
    def test_apuntando_a_sirio_lo_lista_con_sus_coordenadas(self):
        az, alt = self._az_alt_sirio()
        objetos = self.renderer.objetos_visibles(_t(), az, alt)
        nombres = [o["nombre"] for o in objetos]
        self.assertIn("Sirio", nombres)
        sirio = next(o for o in objetos if o["nombre"] == "Sirio")
        self.assertEqual(sirio["tipo"], "estrella")
        # Sirio queda (casi) centrado: su az/alt en la lista coincide con el
        # punto al que apuntamos (tolerancia holgada, FOV 60°).
        self.assertLess(abs(sirio["az"] - az), 0.5)
        self.assertLess(abs(sirio["alt"] - alt), 0.5)
        self.assertLess(sirio["mag"], 0.0)

    @unittest.skipUnless(RUTA_EFEMERIDES.exists(),
                         "Faltan las efemérides de421.bsp (referencia)")
    def test_can_mayor_visible_con_sirio(self):
        az, alt = self._az_alt_sirio()
        nombres = [o["nombre"] for o in
                   self.renderer.objetos_visibles(_t(), az, alt)]
        self.assertIn("Can Mayor", nombres)

    def test_mirando_al_suelo_no_hay_nada(self):
        objetos = self.renderer.objetos_visibles(_t(), 0.0, -89.0)
        self.assertEqual(objetos, [])

    def test_estructura_de_cada_objeto(self):
        objetos = self.renderer.objetos_visibles(_t(), 180.0, 45.0)
        self.assertGreater(len(objetos), 0)
        for o in objetos:
            self.assertIn(o["tipo"], ("estrella", "planeta", "constelacion"))
            for k in ("nombre", "az", "alt"):
                self.assertIn(k, o)
            self.assertIsInstance(o["nombre"], str)
            self.assertTrue(0.0 <= o["az"] < 360.0)
            self.assertTrue(-90.0 <= o["alt"] <= 90.0)
            if o["tipo"] != "constelacion":
                self.assertIsInstance(o["mag"], float)

    def test_ordenado_por_brillo_y_constelaciones_al_final(self):
        objetos = self.renderer.objetos_visibles(_t(), 180.0, 45.0)
        m = [o["mag"] for o in objetos]
        brillantes = [x for x in m if x is not None]
        # Las estrellas/planetas van primero y por brillo (menor = más
        # brillante); ninguna constelación puede aparecer antes.
        self.assertEqual(brillantes, sorted(brillantes))
        visto_none = False
        for x in m:
            if x is None:
                visto_none = True
            else:
                self.assertFalse(visto_none,
                                 "una constelación antes que un astro")
        # Al menos algo de cada tipo en una vista amplia del sur.
        tipos = {o["tipo"] for o in objetos}
        self.assertIn("estrella", tipos)
        self.assertIn("constelacion", tipos)


@unittest.skipUnless(RUTA_CATALOGO.exists(), "Falta el catálogo BSC")
class TestLineasObjetos(unittest.TestCase):
    """El panel de la demo (tecla o) numerado para apuntar con 1-9/0."""

    def setUp(self):
        from compositor.demo_compositor import _lineas_objetos
        self._lineas_objetos = _lineas_objetos
        self.objetos = [
            {"tipo": "estrella", "nombre": "Sirio",
             "az": 137.0, "alt": 53.6, "mag": -1.46},
            {"tipo": "planeta", "nombre": "Júpiter",
             "az": 200.1, "alt": 30.0, "mag": -2.5},
            {"tipo": "constelacion", "nombre": "Can Mayor",
             "az": 138.0, "alt": 50.0, "mag": None},
        ]

    def test_numeracion_1_9_y_0_para_el_decimo(self):
        mas = [{"tipo": "estrella", "nombre": f"E{i}", "az": float(i),
                "alt": 10.0, "mag": 1.0} for i in range(10)]
        lineas = self._lineas_objetos(mas, brujula_activa=False)
        self.assertTrue(any(l.startswith("1 ") for l in lineas))
        self.assertTrue(any(l.startswith("0 ") for l in lineas))  # 10º
        self.assertIn("brújula manual", " ".join(lineas))

    def test_vacio_no_rompe(self):
        lineas = self._lineas_objetos([], brujula_activa=True)
        self.assertIn("ninguno", lineas[1])

    def test_mas_de_10_avisa(self):
        muchos = [{"tipo": "estrella", "nombre": f"E{i}", "az": float(i),
                   "alt": 10.0, "mag": 1.0} for i in range(14)]
        lineas = self._lineas_objetos(muchos, brujula_activa=True)
        self.assertTrue(any("más fuera" in l for l in lineas))


if __name__ == "__main__":
    unittest.main()
