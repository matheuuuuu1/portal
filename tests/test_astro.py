"""Tests de la astrometría (rotación ecuatorial→horizontal, Fase 6)."""

import unittest
from datetime import datetime, timezone

import numpy as np
from skyfield.api import load

from skyrender.astro import (RUTA_EFEMERIDES, altaz_con_skyfield,
                             altaz_desde_horizontal, aplicar_matriz,
                             lst_grados, matriz_horizontal, matriz_vista_camara,
                             precesionar_j2000)
from skyrender.catalogo import RUTA_CATALOGO, cargar_estrellas

# Instante y lugar fijos para los tests de regresión.
_FECHA = datetime(2026, 8, 10, 0, 0, 0, tzinfo=timezone.utc)
_LAT, _LON = 10.0, -70.0

# Estrellas de referencia (RA/Dec J2000 en grados).
_REF = [
    ("Alp And", 2.097, 29.091),
    ("Polaris", 37.9546, 89.2641),
    ("Betelgeuse", 88.7929, 7.4071),
    ("Rigel", 78.467, -8.2016),
    ("Sirius", 101.287, -16.7161),
]


def _tiempo():
    return load.timescale().from_datetime(_FECHA)


class TestLst(unittest.TestCase):
    def test_lst_lon_cero(self):
        self.assertAlmostEqual(lst_grados(0.0, 12.0), 180.0)
        self.assertAlmostEqual(lst_grados(0.0, 0.0), 0.0)

    def test_lst_lon_este(self):
        self.assertAlmostEqual(lst_grados(45.0, 12.0), 225.0)

    def test_lst_envuelve_360(self):
        self.assertAlmostEqual(lst_grados(350.0, 12.0), 530.0 % 360.0)


class TestMatriz(unittest.TestCase):
    def test_matriz_es_rotacion(self):
        M = matriz_horizontal(_LAT, 120.0)
        # M^T M ≈ I (rotación ortogonal)
        self.assertTrue(np.allclose(M.T @ M, np.eye(3), atol=1e-12))

    def test_polo_norte_queda_en_la_latitud(self):
        M = matriz_horizontal(_LAT, 123.0)
        v_polo = aplicar_matriz(M, np.array([[0.0, 0.0, 1.0]]))
        alt, _ = altaz_desde_horizontal(v_polo)
        self.assertAlmostEqual(alt[0], _LAT, delta=1e-9)  # alt del polo = latitud


class TestVistaCamara(unittest.TestCase):
    def test_es_rotacion(self):
        M = matriz_vista_camara(45.0, 20.0, roll_deg=5.0)
        self.assertTrue(np.allclose(M @ M.T, np.eye(3), atol=1e-12))

    def test_apuntando_al_norte_el_norte_va_adelante(self):
        M = matriz_vista_camara(0.0, 0.0)  # cámara al norte, horizontal
        norte = np.array([1.0, 0.0, 0.0])
        coords = M @ norte
        self.assertTrue(np.allclose(coords, [0.0, 0.0, 1.0], atol=1e-12))

    def test_apuntando_al_este_el_este_va_adelante(self):
        M = matriz_vista_camara(90.0, 0.0)
        este = np.array([0.0, 1.0, 0.0])
        coords = M @ este
        self.assertTrue(np.allclose(coords, [0.0, 0.0, 1.0], atol=1e-12))

    def test_inclinacion_90_apunta_al_cenit(self):
        M = matriz_vista_camara(0.0, 90.0)
        cenit = np.array([0.0, 0.0, 1.0])
        coords = M @ cenit
        self.assertTrue(np.allclose(coords, [0.0, 0.0, 1.0], atol=1e-12))


class TestPipeline(unittest.TestCase):
    def _altaz_propios(self, ra_deg, dec_deg, t):
        ra_f, dec_f = precesionar_j2000(np.asarray(ra_deg), np.asarray(dec_deg), t)
        ra = np.radians(ra_f)
        dec = np.radians(dec_f)
        v_eq = np.stack([np.cos(dec) * np.cos(ra),
                         np.cos(dec) * np.sin(ra),
                         np.sin(dec)], axis=1)
        lst = lst_grados(_LON, float(t.gast))
        M = matriz_horizontal(_LAT, lst)
        return altaz_desde_horizontal(aplicar_matriz(M, v_eq))

    @unittest.skipUnless(RUTA_EFEMERIDES.exists(),
                         "faltan las efemérides de421.bsp (referencia)")
    def test_contra_skyfield(self):
        t = _tiempo()
        ra = np.array([r for _, r, _ in _REF])
        dec = np.array([d for _, _, d in _REF])
        alt, az = self._altaz_propios(ra, dec, t)
        alt_ref, az_ref = altaz_con_skyfield(ra, dec, _LAT, _LON, t)
        # La diferencia incluye aberración topocéntrica (~0.006°) y redondeos.
        self.assertTrue(np.allclose(alt, alt_ref, atol=0.1),
                        f"alt propio={alt} vs skyfield={alt_ref}")
        self.assertTrue(np.allclose(az, az_ref, atol=0.1),
                        f"az propio={az} vs skyfield={az_ref}")

    def test_polaris_cerca_del_polo(self):
        t = _tiempo()
        ra, dec = np.array([37.9546]), np.array([89.2641])
        alt, _ = self._altaz_propios(ra, dec, t)
        self.assertAlmostEqual(alt[0], _LAT, delta=1.5)  # alt ≈ latitud ± 1°


class TestCatalogoIntegracion(unittest.TestCase):
    @unittest.skipUnless(RUTA_CATALOGO.exists(),
                         "falta data/catalogo/bsc5.dat")
    def test_betelgeuse_calculable(self):
        catalogo = cargar_estrellas()
        betel = catalogo.buscar("Alp Ori")
        self.assertIsNotNone(betel)
        t = _tiempo()
        ra_f, dec_f = precesionar_j2000(np.array([betel.ra_deg]),
                                        np.array([betel.dec_deg]), t)
        ra = np.radians(ra_f[0])
        dec = np.radians(dec_f[0])
        v_eq = np.array([[np.cos(dec) * np.cos(ra),
                          np.cos(dec) * np.sin(ra), np.sin(dec)]])
        lst = lst_grados(_LON, float(t.gast))
        M = matriz_horizontal(_LAT, lst)
        alt, az = altaz_desde_horizontal(aplicar_matriz(M, v_eq))
        self.assertGreater(alt[0], -90.0)
        self.assertLessEqual(alt[0], 90.0)
        self.assertGreaterEqual(az[0], 0.0)
        self.assertLess(az[0], 360.0)


if __name__ == "__main__":
    unittest.main()
