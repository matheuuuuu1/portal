"""Tests de construcción y validación del cuadrilátero del marco."""

import unittest

from handtracking import gesture, quadrilateral
from handtracking.detector import HandData, TIP_INDICE, TIP_MEDIO, TIP_PULGAR


class _LM:
    def __init__(self, x, y, z=0.0):
        self.x = x
        self.y = y
        self.z = z


def hand_marco(esq_sup, esq_inf, handedness):
    """Mano cuyos dos dedos activos están en esq_sup y esq_inf."""
    lms = [_LM(0.5, 0.5) for _ in range(21)]
    lms[TIP_PULGAR] = _LM(*esq_sup)
    lms[TIP_INDICE] = _LM(*esq_inf)
    lms[TIP_MEDIO] = _LM(*esq_inf)
    return HandData(handedness=handedness, score=0.9, landmarks=lms)


class TestBuildQuad(unittest.TestCase):
    def test_cuatro_esquinas_ordenadas_TL_TR_BR_BL(self):
        # mano izquierda: arriba-izquierda y abajo-izquierda
        izq = hand_marco((0.1, 0.2), (0.1, 0.8), "Left")
        # mano derecha: arriba-derecha y abajo-derecha
        der = hand_marco((0.9, 0.2), (0.9, 0.8), "Right")
        quad = quadrilateral.build_quad([izq, der], gesture.MODO_L)
        self.assertIsNotNone(quad)
        # TL: x pequeña y y pequeña; TR: x grande y pequeña; etc.
        tl, tr, br, bl = quad
        self.assertTrue(tl[0] < tr[0] and tl[1] < bl[1])
        self.assertTrue(tr[0] > tl[0] and tr[1] < br[1])
        self.assertTrue(br[0] > bl[0] and br[1] > tr[1])
        self.assertTrue(bl[0] < br[0] and bl[1] > tl[1])

    def test_requiere_dos_manos(self):
        der = hand_marco((0.9, 0.2), (0.9, 0.8), "Right")
        self.assertIsNone(quadrilateral.build_quad([der], gesture.MODO_L))

    def test_mano_completa_usa_las_mismas_esquinas(self):
        # en MANO_COMPLETA el marco se forma igual que en L (pulgar+índice)
        izq = hand_marco((0.1, 0.2), (0.1, 0.8), "Left")
        der = hand_marco((0.9, 0.2), (0.9, 0.8), "Right")
        quad_l = quadrilateral.build_quad([izq, der], gesture.MODO_L)
        quad_mc = quadrilateral.build_quad([izq, der], gesture.MODO_MANO_COMPLETA)
        self.assertEqual(quad_l, quad_mc)

    def test_modo_desconocido_devuelve_none(self):
        izq = hand_marco((0.1, 0.2), (0.1, 0.8), "Left")
        der = hand_marco((0.9, 0.2), (0.9, 0.8), "Right")
        self.assertIsNone(quadrilateral.build_quad([izq, der], "X"))


class TestValidateQuad(unittest.TestCase):
    def test_area_minima_ok(self):
        quad = [(0.1, 0.2), (0.9, 0.2), (0.9, 0.8), (0.1, 0.8)]
        self.assertTrue(quadrilateral.validate_quad(quad))

    def test_marco_degenerado_rechazado(self):
        # marco casi colapsado (puntos muy juntos) -> área casi nula
        quad = [(0.3, 0.3), (0.7, 0.3), (0.71, 0.31), (0.31, 0.31)]
        self.assertLess(quadrilateral.polygon_area(quad), quadrilateral.MIN_AREA)
        self.assertFalse(quadrilateral.validate_quad(quad))

    def test_cuadrilatero_none_rechazado(self):
        self.assertFalse(quadrilateral.validate_quad(None))
        self.assertFalse(quadrilateral.validate_quad([(0.1, 0.1)]))

    def test_area_shoelace_rectangulo(self):
        quad = [(0.1, 0.2), (0.9, 0.2), (0.9, 0.8), (0.1, 0.8)]
        self.assertAlmostEqual(quadrilateral.polygon_area(quad), 0.48, places=6)


if __name__ == "__main__":
    unittest.main()
