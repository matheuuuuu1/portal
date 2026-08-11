"""Tests de la composición: incrustar el cielo dentro del marco (Fase 8).

Verifican la homografía, el warp y, sobre todo, el criterio de "hecho" de la
fase: el cielo aparece dentro del cuadrilátero del marco y el resto del frame
permanece intacto.
"""

import time
import unittest

import cv2
import numpy as np

from compositor.compositor import (Compositor, homografia_marco,
                                   mascara_marco, quad_a_pixeles)

ANCHO, ALTO = 1280, 720


def _frame_gradiente():
    """Frame BGR con un patrón distinto en cada píxel (no confundible con verde)."""
    y, x = np.mgrid[0:ALTO, 0:ANCHO]
    frame = np.zeros((ALTO, ANCHO, 3), dtype=np.uint8)
    frame[..., 0] = (x // 8) % 256
    frame[..., 1] = (y // 8) % 256
    frame[..., 2] = ((x + y) // 16) % 256
    return frame


def _cielo_verde():
    return np.full((ALTO, ANCHO, 3), (0, 255, 0), dtype=np.uint8)


# Marco centrado y bien dentro del frame, en coordenadas normalizadas.
QUAD = [(0.3, 0.3), (0.7, 0.3), (0.7, 0.7), (0.3, 0.7)]


class TestHomografia(unittest.TestCase):
    def test_mapea_las_esquinas_del_cielo_a_las_del_marco(self):
        quad_px = quad_a_pixeles(QUAD, ANCHO, ALTO)
        M = homografia_marco(quad_px, ANCHO, ALTO)
        src = np.array([[[0, 0], [ANCHO - 1, 0],
                         [ANCHO - 1, ALTO - 1], [0, ALTO - 1]]],
                       dtype=np.float32)
        proyectado = cv2.perspectiveTransform(src, M)[0]
        for p, esperado in zip(proyectado, quad_px):
            self.assertAlmostEqual(float(p[0]), float(esperado[0]), places=3)
            self.assertAlmostEqual(float(p[1]), float(esperado[1]), places=3)

    def test_marco_completo_es_identidad_aproximada(self):
        # Marco que cubre todo el frame -> el centro del cielo cae en el centro.
        quad_px = quad_a_pixeles([(0, 0), (1, 0), (1, 1), (0, 1)], ANCHO, ALTO)
        M = homografia_marco(quad_px, ANCHO, ALTO)
        p = cv2.perspectiveTransform(
            np.array([[[ANCHO / 2, ALTO / 2]]], dtype=np.float32), M)[0][0]
        # tolerancia de ±1 px por el factor (ancho-1)/ancho
        self.assertAlmostEqual(float(p[0]), ANCHO / 2, delta=1.0)
        self.assertAlmostEqual(float(p[1]), ALTO / 2, delta=1.0)

    def test_quad_a_pixeles(self):
        px = quad_a_pixeles(QUAD, ANCHO, ALTO)
        esperado = [(384.0, 216.0), (896.0, 216.0),
                    (896.0, 504.0), (384.0, 504.0)]
        for p, e in zip(px, esperado):
            self.assertAlmostEqual(p[0], e[0], places=6)
            self.assertAlmostEqual(p[1], e[1], places=6)


class TestComposicion(unittest.TestCase):
    def setUp(self):
        self.compositor = Compositor(ancho=ANCHO, alto=ALTO, borde_suave=0.0)
        self.frame = _frame_gradiente()
        self.cielo = _cielo_verde()

    def test_cielo_incrustado_dentro_del_marco(self):
        salida = self.compositor.compone(self.frame, self.cielo, QUAD)
        # El centro del marco cae dentro del cuadrilátero y debe ser el cielo.
        np.testing.assert_array_equal(salida[ALTO // 2, ANCHO // 2], (0, 255, 0))
        # Una esquina interior del marco (cerca de TL) también es cielo.
        np.testing.assert_array_equal(salida[300, 450], (0, 255, 0))

    def test_resto_del_frame_intacto(self):
        salida = self.compositor.compone(self.frame, self.cielo, QUAD)
        # Píxeles claramente fuera del marco: deben quedar idénticos al frame.
        for (x, y) in [(10, 10), (1270, 10), (1270, 710), (10, 710),
                       (100, 100), (640, 100), (640, 650)]:
            np.testing.assert_array_equal(salida[y, x], self.frame[y, x])

    def test_dimensiones_y_tipo(self):
        salida = self.compositor.compone(self.frame, self.cielo, QUAD)
        self.assertEqual(salida.shape, (ALTO, ANCHO, 3))
        self.assertEqual(salida.dtype, np.uint8)

    def test_sin_marco_devuelve_el_frame(self):
        salida = self.compositor.compone(self.frame, self.cielo, None)
        self.assertIs(salida, self.frame)

    def test_marco_degenerado_rechazado(self):
        degenerado = [(0.3, 0.3), (0.7, 0.3), (0.71, 0.31), (0.31, 0.31)]
        salida = self.compositor.compone(self.frame, self.cielo, degenerado)
        self.assertIs(salida, self.frame)

    def test_marco_con_menos_de_cuatro_puntos(self):
        salida = self.compositor.compone(self.frame, self.cielo,
                                         [(0.1, 0.1), (0.9, 0.1)])
        self.assertIs(salida, self.frame)

    def test_marco_rotado_incrusta_cielo_rotado(self):
        # Marco "al revés": BR y TL intercambiados -> el cielo aparece volteado.
        rotado = [QUAD[2], QUAD[1], QUAD[0], QUAD[3]]
        salida = self.compositor.compone(self.frame, self.cielo, rotado)
        # El centro sigue cayendo dentro del marco y es el cielo.
        np.testing.assert_array_equal(salida[ALTO // 2, ANCHO // 2], (0, 255, 0))

    def test_rendimiento_objetivo(self):
        compositor = Compositor(ancho=ANCHO, alto=ALTO, borde_suave=2.0)
        compositor.compone(self.frame, self.cielo, QUAD)  # calienta
        inicio = time.perf_counter()
        for _ in range(30):
            compositor.compone(self.frame, self.cielo, QUAD)
        total = time.perf_counter() - inicio
        promedio_ms = total / 30.0 * 1000.0
        self.assertLess(promedio_ms, 50.0,
                        f"la composición es demasiado lenta: {promedio_ms:.1f} ms")


class TestBordeSuave(unittest.TestCase):
    def test_funde_el_borde_y_mantiene_el_interior(self):
        duro = Compositor(ancho=ANCHO, alto=ALTO, borde_suave=0.0)
        suave = Compositor(ancho=ANCHO, alto=ALTO, borde_suave=3.0)
        frame = _frame_gradiente()
        cielo = _cielo_verde()
        out_duro = duro.compone(frame, cielo, QUAD)
        out_suave = suave.compone(frame, cielo, QUAD)
        # El interior del marco sigue siendo el cielo en ambos.
        np.testing.assert_array_equal(out_duro[ALTO // 2, ANCHO // 2], (0, 255, 0))
        np.testing.assert_array_equal(out_suave[ALTO // 2, ANCHO // 2], (0, 255, 0))
        # En la transición del borde las imágenes difieren (una funde, la otra no).
        x_borde = int(0.3 * ANCHO) + 1
        self.assertFalse(np.array_equal(out_duro[ALTO // 2, x_borde],
                                        out_suave[ALTO // 2, x_borde]))

    def test_mascara_valores_en_rango(self):
        quad_px = quad_a_pixeles(QUAD, ANCHO, ALTO)
        m = mascara_marco(quad_px, ANCHO, ALTO, borde_suave=2.0)
        self.assertEqual(m.shape, (ALTO, ANCHO))
        self.assertLessEqual(float(m.max()), 1.0)
        self.assertGreaterEqual(float(m.min()), 0.0)
        self.assertGreater(float(m[ALTO // 2, ANCHO // 2]), 0.99)


if __name__ == "__main__":
    unittest.main()
