"""Tests de extras de la demo: espejo de cámara y panel de información (tecla i).

El espejo voltea la imagen compuesta (modo selfie: la mano derecha sale a la
derecha) y el cielo junto con la escena. El panel `i` dibuja un recuadro
semitransparente con todas las métricas en la esquina superior izquierda.
"""

import time
import unittest

import cv2
import numpy as np

from compositor.demo_compositor import (CompassReader, _dibujar_panel_info,
                                        espejar)


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


if __name__ == "__main__":
    unittest.main()
