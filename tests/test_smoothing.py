"""Tests del suavizado exponencial del marco."""

import unittest

from handtracking.smoothing import QuadSmoother


class TestQuadSmoother(unittest.TestCase):
    def test_primer_update_devuelve_el_valor(self):
        sm = QuadSmoother(alpha=0.4)
        pts = [(0.1, 0.2), (0.9, 0.2), (0.9, 0.8), (0.1, 0.8)]
        self.assertEqual(sm.update(pts), pts)

    def test_converge_a_valor_constante(self):
        sm = QuadSmoother(alpha=0.5)
        pts = [(0.1, 0.2), (0.9, 0.2), (0.9, 0.8), (0.1, 0.8)]
        for _ in range(20):
            out = sm.update(pts)
        for p, expected in zip(out, pts):
            self.assertAlmostEqual(p[0], expected[0], places=6)
            self.assertAlmostEqual(p[1], expected[1], places=6)

    def test_suaviza_transicion(self):
        sm = QuadSmoother(alpha=0.5)
        sm.update([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)])
        out = sm.update([(1.0, 1.0), (0.0, 1.0), (0.0, 0.0), (1.0, 0.0)])
        # el primer punto del marco pasa de 0.0 a 0.5, no a 1.0
        self.assertAlmostEqual(out[0][0], 0.5, places=6)

    def test_reset_limpia_la_memoria(self):
        sm = QuadSmoother(alpha=0.5)
        sm.update([(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)])
        sm.reset()
        pts = [(0.5, 0.5)] * 4
        self.assertEqual(sm.update(pts), pts)

    def test_alpha_invalida(self):
        with self.assertRaises(ValueError):
            QuadSmoother(alpha=1.5)
        with self.assertRaises(ValueError):
            QuadSmoother(alpha=0.0)


if __name__ == "__main__":
    unittest.main()
