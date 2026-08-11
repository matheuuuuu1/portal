"""Tests del catálogo de estrellas (BSC, Fase 6)."""

import unittest

import numpy as np

from skyrender.catalogo import RUTA_CATALOGO, cargar_estrellas


def _skip_sin_catalogo(fn):
    return unittest.skipUnless(RUTA_CATALOGO.exists(),
                               "falta data/catalogo/bsc5.dat (descargar con "
                               "tools/download_models.py) ")(fn)


class TestCatalogo(unittest.TestCase):
    @_skip_sin_catalogo
    def test_carga_y_cuenta(self):
        cat = cargar_estrellas()
        # El BSC tiene 9.110 estrellas; con mag<=6.5 quedan ~9.000.
        self.assertGreater(cat.n, 8000)
        self.assertLessEqual(cat.n, 9110)

    @_skip_sin_catalogo
    def test_alf_and_posicion(self):
        cat = cargar_estrellas()
        e = cat.buscar("Alp And")
        self.assertIsNotNone(e)
        # Alp And: RA 00h08m23.3s = 2.097°, Dec +29°05'26" = 29.091°, Vmag 2.06.
        self.assertAlmostEqual(e.ra_deg, 2.097, delta=0.01)
        self.assertAlmostEqual(e.dec_deg, 29.091, delta=0.01)
        self.assertAlmostEqual(e.mag, 2.06, delta=0.01)

    @_skip_sin_catalogo
    def test_contiene_polaris(self):
        cat = cargar_estrellas()
        e = cat.buscar("Alp UMi")  # el BSC llama a Polaris "1Alp UMi"
        self.assertIsNotNone(e)
        self.assertAlmostEqual(e.dec_deg, 89.26, delta=0.2)  # dec ~ +89.26°

    @_skip_sin_catalogo
    def test_vectores_ecuatoriales_base(self):
        cat = cargar_estrellas()
        v = cat.vectores_ecuatoriales()
        self.assertEqual(v.shape, (cat.n, 3))
        # norma unitaria
        normas = np.linalg.norm(v, axis=1)
        self.assertTrue(np.allclose(normas, 1.0, atol=1e-12))

    @_skip_sin_catalogo
    def test_formato_hyg_no_soportado_aun(self):
        with self.assertRaises(ValueError):
            cargar_estrellas(formato="hyg")

    def test_catalogo_ausente_da_mensaje_claro(self):
        # Robustez (Fase 10): si falta el catálogo, el error dice cómo
        # descargarlo, no un FileNotFoundError con la ruta pelada.
        with self.assertRaises(FileNotFoundError) as ctx:
            cargar_estrellas(ruta="data/catalogo/no-existe.dat")
        mensaje = str(ctx.exception)
        self.assertIn("download_models", mensaje)


if __name__ == "__main__":
    unittest.main()
