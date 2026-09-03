"""Tests de extras de la demo: espejo de cámara y panel de información (tecla i).

El espejo voltea la imagen compuesta (modo selfie: la mano derecha sale a la
derecha) y el cielo junto con la escena. El panel `i` dibuja un recuadro
semitransparente con todas las métricas en la esquina superior izquierda.
"""

import time
import unittest
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np

from compositor.compositor import Compositor
from compositor.demo_compositor import (CompassReader, _dibujar_panel_info,
                                        _ubicacion, espejar)


def _frame_simple(ancho=320, alto=240):
    """Frame negro con un cuadrado blanco en la esquina superior izquierda."""
    img = np.zeros((alto, ancho, 3), dtype=np.uint8)
    img[10:20, 10:20] = (255, 255, 255)
    return img


class TestEspejo(unittest.TestCase):
    def test_espejo_mueve_el_contenido_a_la_derecha(self):
        frame = _frame_simple()
        volteada = espejar(frame, True)
        # El cuadrado blanco (10..19) pasa a (300..309) tras la reflexión.
        self.assertTrue(bool(volteada[15, 304].any()),
                        "el espejo no movió el cuadrado a la derecha")
        self.assertFalse(bool(volteada[15, 15].any()),
                         "el espejo dejó el cuadrado en la izquierda")

    def test_espejo_preserva_dimensiones_y_tipo(self):
        frame = _frame_simple()
        volteada = espejar(frame, True)
        self.assertEqual(volteada.shape, frame.shape)
        self.assertEqual(volteada.dtype, frame.dtype)

    def test_sin_espejo_devuelve_la_misma_imagen(self):
        frame = _frame_simple()
        misma = espejar(frame, False)
        self.assertIs(misma, frame)

    def test_espejo_es_una_reflexion_horizontal(self):
        # Una reflexión aplicada dos veces devuelve el original.
        frame = _frame_simple()
        doble = espejar(espejar(frame, True), True)
        np.testing.assert_array_equal(doble, frame)


class TestEspejoNoVolteaElCielo(unittest.TestCase):
    """El espejo voltea la cámara, NO el cielo: los nombres de astros deben
    quedar legibles. Regresión del bug en que se volteaba la imagen final y
    las etiquetas del cielo salían invertidas."""

    def test_la_escena_se_espeja_pero_el_cielo_queda_legible(self):
        ancho, alto = 320, 240
        # "Mano derecha": mancha roja a la izquierda en el frame crudo.
        frame = np.zeros((alto, ancho, 3), dtype=np.uint8)
        frame[20:40, 20:60] = (0, 0, 255)
        # Cielo con texto legible "ESTE" en la mitad izquierda del marco.
        cielo = np.zeros((alto, ancho, 3), dtype=np.uint8)
        cv2.putText(cielo, "ESTE", (40, 120), cv2.FONT_HERSHEY_SIMPLEX,
                    1.5, (255, 255, 255), 3)
        comp = Compositor(ancho=ancho, alto=alto, borde_suave=0.0)
        quad_izq = [(0, 0), (0.5, 0), (0.5, 1), (0, 1)]

        # Flujo real: se voltea el frame (selfie) y se compone el cielo SIN
        # voltear. La ventana cubre la mitad izquierda.
        salida = comp.compone(espejar(frame, True), cielo, quad_izq)

        # 1) El cielo dentro del marco queda como está (texto legible).
        np.testing.assert_array_equal(salida[20:220, 20:140],
                                      cielo[20:220, 20:140])
        # 2) No es el cielo espejado (los nombres no se invierten).
        self.assertFalse(np.array_equal(salida[20:220, 20:140],
                                        espejar(cielo, True)[20:220, 20:140]),
                         "el cielo está invertido: los nombres saldrían al revés")
        # 3) La "mano derecha" (mancha roja) pasó a la derecha de la escena.
        self.assertTrue(bool(salida[30, 280].any()),
                        "la mano derecha debería verse a la derecha")


class TestPanelInfo(unittest.TestCase):
    def setUp(self):
        self.frame = _frame_simple()
        self.lineas = [
            "FPS: 27.2   rumbo 183.0   incl 42.1   roll +0.0",
            "gesto: L   etiquetas: auto (no)",
            "estética: noche_profunda   marco: ventana   brillo: 2.50",
            "brújula: sin servidor (teclado)",
        ]

    def test_pinta_pixeles_del_panel(self):
        antes = self.frame.copy()
        _dibujar_panel_info(self.frame, self.lineas)
        # El recuadro oscurece la esquina superior izquierda.
        self.assertFalse(np.array_equal(self.frame, antes))

    def test_no_modifica_dimensiones_ni_tipo(self):
        _dibujar_panel_info(self.frame, self.lineas)
        self.assertEqual(self.frame.shape, (240, 320, 3))
        self.assertEqual(self.frame.dtype, np.uint8)

    def test_lineas_vacias_no_rompen(self):
        img = _frame_simple()
        _dibujar_panel_info(img, [])
        np.testing.assert_array_equal(img, _frame_simple())

    def test_panel_supera_las_dimensiones_sin_error(self):
        # Panel más ancho que la imagen: no debe lanzar (el texto se recorta).
        img = np.zeros((20, 40, 3), dtype=np.uint8)
        largas = ["una línea muy larga que excede el ancho del frame",
                  "otra línea también larga"]
        _dibujar_panel_info(img, largas)
        self.assertEqual(img.shape, (20, 40, 3))


class TestCompassReaderEdad(unittest.TestCase):
    def test_sin_lectura_devuelve_none(self):
        lector = CompassReader("https://localhost:8080")
        self.assertIsNone(lector.edad())

    def test_con_lectura_devuelve_los_segundos(self):
        lector = CompassReader("https://localhost:8080")
        lector._estado = {"rumbo": 10.0}
        lector._ts = time.time() - 2.0
        self.assertAlmostEqual(lector.edad(), 2.0, delta=0.3)

    def test_edad_crece_con_el_tiempo(self):
        lector = CompassReader("https://localhost:8080")
        lector._estado = {"rumbo": 10.0}
        lector._ts = time.time() - 5.0
        self.assertGreater(lector.edad(), 4.0)


class TestUbicacionArgs(unittest.TestCase):
    """Regresión 1.3: `_ubicacion` respeta `--lat/--lon` de la línea de
    comandos (que luego se pasa al SkyRenderer para que las efemérides de los
    planetas usen la misma posición que las estrellas)."""

    def test_lat_lon_distintos_de_la_guardada(self):
        args = SimpleNamespace(lat=40.0, lon=-3.7)
        u = _ubicacion(args)
        self.assertEqual(u.lat, 40.0)
        self.assertEqual(u.lon, -3.7)
        self.assertEqual(u.nombre, "demo")

    def test_sin_lat_lon_cae_a_la_guardada_o_por_defecto(self):
        args = SimpleNamespace(lat=None, lon=None)
        u = _ubicacion(args)
        self.assertIsNotNone(u)


class TestCelularHTMLCalibracion(unittest.TestCase):
    """Regresión 1.4: el botón Calibrar se habilita con la primera lectura
    válida del sensor, no al activarlo; y alpha nulo no se falsifica a 0.

    Es un test de contenido (no hay runner de JS): verifica que el HTML tiene
    la lógica correcta de habilitación y protección.
    """

    @classmethod
    def setUpClass(cls):
        ruta = (Path(__file__).resolve().parents[1] / "src" / "server"
                / "static" / "celular.html")
        cls.html = ruta.read_text(encoding="utf-8")

    def test_no_habilita_al_activar_sensor(self):
        # En el bloque de `btn.onclick` ya no está `btnCal.disabled = false`.
        onclick = self.html.split("btn.onclick")[1].split("btnCal.onclick")[0]
        self.assertNotIn("btnCal.disabled = false", onclick)

    def test_habilita_con_la_primera_lectura(self):
        # El flag `primeraLectura` y la habilitación existen en el manejador
        # de orientación.
        self.assertIn("primeraLectura", self.html)
        self.assertIn("btnCal.disabled = false", self.html)

    def test_alpha_nulo_no_se_convierte_en_cero(self):
        # La línea vieja `(e.alpha === null) ? 0 : e.alpha` desapareció y el
        # manejador rechaza alpha nulo antes de habilitar calibrar.
        self.assertNotIn("(e.alpha === null) ? 0", self.html)
        self.assertIn("if (e.alpha === null)", self.html)

    def test_calibrar_protege_sin_primera_lectura(self):
        self.assertIn("Espera la primera lectura del sensor", self.html)


if __name__ == "__main__":
    unittest.main()
