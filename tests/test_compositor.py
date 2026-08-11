"""Tests de la composición: incrustar el cielo dentro del marco (Fase 8).

Verifican los dos modos de `Compositor` y, sobre todo, el criterio de "hecho"
de la fase: el cielo aparece dentro del cuadrilátero del marco y el resto del
frame permanece intacto. El modo por defecto ("ventana") muestra solo el
pedazo de cielo que cae bajo el marco (anclado a la cámara); "completo"
comprime todo el FOV dentro del marco (warp).
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


def _cielo_mancha_centro():
    """Render sintético: negro salvo una mancha verde en el centro exacto.

    Distingue los dos modos: en "ventana" la mancha solo se ve si el marco la
    cubre (el cielo está anclado a la cámara); en "completo" la mancha siempre
    aparece porque todo el cielo se comprime dentro del marco.
    """
    cielo = np.zeros((ALTO, ANCHO, 3), dtype=np.uint8)
    cielo[ALTO // 2 - 4:ALTO // 2 + 5, ANCHO // 2 - 4:ANCHO // 2 + 5] = (0, 255, 0)
    return cielo


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

    def test_cielo_a_menor_resolucion_se_escala_al_frame(self):
        # Fase 10: el render puede venir a 540p (mismo FOV, menos píxeles); el
        # compositor lo escala al tamaño del frame. La mancha del centro del
        # render 960x540 cae en el centro del frame 1280x720.
        comp = Compositor(ancho=ANCHO, alto=ALTO, borde_suave=0.0)
        cielo = np.zeros((540, 960, 3), dtype=np.uint8)
        cielo[270 - 4:270 + 5, 480 - 4:480 + 5] = (0, 255, 0)
        salida = comp.compone(self.frame, cielo, QUAD)
        np.testing.assert_array_equal(salida[ALTO // 2, ANCHO // 2], (0, 255, 0))
        # El resto del frame fuera del marco sigue intacto.
        np.testing.assert_array_equal(salida[10, 10], self.frame[10, 10])

    def test_modo_completo_con_cielo_reducido_no_rompe(self):
        # El warp "completo" también acepta un cielo a menor resolución.
        comp = Compositor(ancho=ANCHO, alto=ALTO, borde_suave=0.0,
                          modo="completo")
        cielo = np.zeros((360, 640, 3), dtype=np.uint8)
        cielo[180 - 4:180 + 5, 320 - 4:320 + 5] = (0, 255, 0)
        salida = comp.compone(self.frame, cielo, QUAD)
        self.assertEqual(salida.shape, (ALTO, ANCHO, 3))
        region = salida[ALTO // 2 - 5:ALTO // 2 + 6, ANCHO // 2 - 5:ANCHO // 2 + 6]
        verde_puro = (region[:, :, 1] == 255) & (region[:, :, 0] == 0)
        self.assertTrue(bool(verde_puro.any()),
                        "la mancha del centro debería verse en el marco")

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

    def test_marco_invertido_no_rompe(self):
        # Orden de esquinas "al revés" (BR y TL intercambiados): en ambos
        # modos el marco sigue incrustando el cielo y no rompe la composición.
        rotado = [QUAD[2], QUAD[1], QUAD[0], QUAD[3]]
        salida = self.compositor.compone(self.frame, self.cielo, rotado)
        # El centro del frame cae dentro del marco y es el cielo.
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


class TestModoVentana(unittest.TestCase):
    """Modo "ventana": el marco revela el cielo anclado a la cámara.

    El render ocupa la cámara completa (misma resolución y FOV); el marco
    solo muestra el pedazo de cielo que cae debajo de él, sin warp.
    """

    def setUp(self):
        self.frame = _frame_gradiente()
        self.cielo = _cielo_mancha_centro()

    def test_el_marco_recorta_el_cielo_anclado(self):
        comp = Compositor(ancho=ANCHO, alto=ALTO, borde_suave=0.0,
                          modo="ventana")
        # Marco centrado: la mancha del centro del render queda bajo el marco.
        salida = comp.compone(self.frame, self.cielo, QUAD)
        np.testing.assert_array_equal(salida[ALTO // 2, ANCHO // 2], (0, 255, 0))
        # Un punto dentro del marco pero lejos de la mancha es NEGRO (el
        # render es negro ahí), no el frame: el cielo está anclado a la
        # cámara y no se comprime ni se desplaza dentro del marco.
        x, y = int(0.4 * ANCHO), int(0.6 * ALTO)
        np.testing.assert_array_equal(salida[y, x], (0, 0, 0))

    def test_el_pedazo_depende_de_la_posicion_del_marco(self):
        comp = Compositor(ancho=ANCHO, alto=ALTO, borde_suave=0.0,
                          modo="ventana")
        # Marco arriba a la izquierda: la mancha (centro del render) queda
        # FUERA del marco, así que dentro del marco no hay verde.
        quad_tl = [(0.05, 0.05), (0.3, 0.05), (0.3, 0.3), (0.05, 0.3)]
        salida = comp.compone(self.frame, self.cielo, quad_tl)
        cx, cy = int(0.175 * ANCHO), int(0.175 * ALTO)
        np.testing.assert_array_equal(salida[cy, cx], (0, 0, 0))
        # Y el centro del render (640, 360) queda fuera del marco: el frame
        # sigue intacto ahí (el cielo no se dibuja desplazado).
        np.testing.assert_array_equal(salida[ALTO // 2, ANCHO // 2],
                                      self.frame[ALTO // 2, ANCHO // 2])

    def test_modo_completo_comprime_todo_el_cielo(self):
        # Contraste: en "completo" el cielo entero se warpea al marco, así
        # que la mancha del centro aparece aunque el marco esté a un lado.
        comp = Compositor(ancho=ANCHO, alto=ALTO, borde_suave=0.0,
                          modo="completo")
        quad_tl = [(0.05, 0.05), (0.3, 0.05), (0.3, 0.3), (0.05, 0.3)]
        salida = comp.compone(self.frame, self.cielo, quad_tl)
        cx, cy = int(0.175 * ANCHO), int(0.175 * ALTO)
        # La mancha del centro del cielo se comprime dentro del marco: en la
        # vecindad del centro del marco debe aparecer verde puro. (La
        # interpolación del warp deja el píxel exacto a media intensidad y la
        # precisión flotante desvía ±1 px; el frame nunca tiene verde 255 con
        # rojo 0 en esa zona, así que la comprobación es inequívoca.)
        region = salida[cy - 3:cy + 4, cx - 3:cx + 4]
        verde_puro = (region[:, :, 1] == 255) & (region[:, :, 0] == 0)
        self.assertTrue(bool(verde_puro.any()),
                        "la mancha del centro debería verse en el marco")

    def test_modo_invalido_lanza(self):
        with self.assertRaises(ValueError):
            Compositor(ancho=ANCHO, alto=ALTO, modo="no-existe")


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
