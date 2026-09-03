"""Tests del launcher unificado (Fase 11, src/app/main.py)."""

import contextlib
import io
import socket
import threading
import unittest
from unittest.mock import patch

from app.main import (_arrancar_servidor, _verificar_certificado,
                      _verificar_prerequisitos, main)


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


class TestArrancarServidorPuertoOcupado(unittest.TestCase):
    """Regresión 1.1: un puerto ocupado debe reportarse, no tragarse.

    Antes, `_arrancar_servidor` hacía `except Exception: pass` y el launcher
    imprimía las instrucciones como si todo fuera bien, con la demo corriendo
    sin brújula para siempre.
    """

    def _puerto_ocupado(self) -> int:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        self.addCleanup(s.close)
        return s.getsockname()[1]

    def test_puerto_ocupado_deja_el_error_accesible(self):
        port = self._puerto_ocupado()
        arrancado = threading.Event()
        error: dict = {}
        hilo = threading.Thread(
            target=_arrancar_servidor,
            args=("127.0.0.1", port, False, arrancado, error),
            daemon=True)
        hilo.start()
        self.assertTrue(arrancado.wait(timeout=15.0),
                        "el hilo debe confirmar el arranque (éxito o error)")
        self.assertIn("excepcion", error,
                      "el error del puerto ocupado debe quedar accesible")
        self.assertIsInstance(error["excepcion"], OSError)
        self.assertIn("mensaje", error)
        hilo.join(timeout=10.0)

    def test_main_devuelve_1_con_puerto_ocupado(self):
        """El launcher completo debe abortar (código 1) y no seguir a la demo.

        Con el host explícito en 127.0.0.1 (misma interfaz que el socket que
        ocupa el puerto), Windows rechaza el bind y el launcher debe reportarlo.
        """
        port = self._puerto_ocupado()
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            codigo = main(["--host", "127.0.0.1", "--port", str(port),
                           "--no-tls", "--camera", "999"])
        self.assertEqual(codigo, 1)
        self.assertIn("no se pudo arrancar el servidor", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
