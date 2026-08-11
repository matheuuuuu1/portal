"""Tests del launcher unificado (Fase 11, src/app/main.py)."""

import unittest
from unittest.mock import patch

from app.main import _verificar_prerequisitos, _verificar_certificado


class TestVerificarPrerequisitos(unittest.TestCase):
    """La función de verificación debe detectar archivos faltantes."""

    @patch("pathlib.Path.exists", return_value=True)
    def test_todo_presente_devuelve_vacio(self, _mock):
        """Si existen modelo, efemérides y catálogo, no hay errores."""
        errores = _verificar_prerequisitos()
        self.assertEqual(errores, [])

    def test_falta_modelo_manos(self):
        """Si falta hand_landmarker.task, hay un error con 'download_models'."""
        def _existe(self_path):
            return "hand_landmarker" not in str(self_path)

        with patch("pathlib.Path.exists", _existe):
            errores = _verificar_prerequisitos()
        self.assertEqual(len(errores), 1)
        self.assertIn("download_models", errores[0])

    def test_falta_efemerides(self):
        """Si falta de421.bsp, hay un error."""
        def _existe(self_path):
            return "de421" not in str(self_path)

        with patch("pathlib.Path.exists", _existe):
            errores = _verificar_prerequisitos()
        self.assertEqual(len(errores), 1)
        self.assertIn("download_models", errores[0])

    @patch("pathlib.Path.exists", return_value=False)
    def test_faltan_todos(self, _mock):
        """Si faltan los tres archivos, hay tres errores."""
        errores = _verificar_prerequisitos()
        self.assertEqual(len(errores), 3)


class TestVerificarCertificado(unittest.TestCase):
    """La verificación del certificado depende del flag TLS."""

    def test_sin_tls_no_verifica(self):
        """Con --no-tls no se verifican los certificados."""
        errores = _verificar_certificado(tls=False)
        self.assertEqual(errores, [])

    @patch("pathlib.Path.exists", return_value=True)
    def test_tls_con_certificados(self, _mock):
        """Con TLS y certificados presentes, no hay errores."""
        errores = _verificar_certificado(tls=True)
        self.assertEqual(errores, [])

    @patch("pathlib.Path.exists", return_value=False)
    def test_tls_sin_certificados(self, _mock):
        """Con TLS y certificados faltantes, hay errores."""
        errores = _verificar_certificado(tls=True)
        self.assertGreater(len(errores), 0)
        self.assertIn("gen_cert", errores[0])


if __name__ == "__main__":
    unittest.main()
