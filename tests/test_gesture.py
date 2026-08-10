"""Tests de la selección del modo de gesto (ADR-004, validado por el usuario).

Usan un landmark dummy para no depender de los tipos de MediaPipe.
"""

import unittest

from handtracking import gesture
from handtracking.detector import HandData


class _LM:
    def __init__(self, x=0.5, y=0.5, z=0.0):
        self.x = x
        self.y = y
        self.z = z


def make_hand(indice_y, medio_y, pulgar_extendido, handedness="Right"):
    """Construye una mano con índice/medio configurados y pulgar por distancia.

    Índice y medio están extendidos si su tip (y) queda por debajo de su PIP
    con el margen de la heurística (PIP en y=0.4). El pulgar se controla por
    distancia: MCP(2) en (0.5, 0.4), IP(3) en (0.5, 0.35); extendido si el
    tip(4) se aleja claramente (0.2) y plegado si queda cerca (0.028 < 0.055).
    """
    lms = [_LM() for _ in range(21)]
    lms[2] = _LM(0.5, 0.4)   # MCP pulgar
    lms[3] = _LM(0.5, 0.35)  # IP pulgar (d(3,2) = 0.05)
    lms[4] = _LM(0.5, 0.2) if pulgar_extendido else _LM(0.52, 0.38)
    lms[6] = _LM(0.5, 0.4)   # PIP índice
    lms[8] = _LM(0.5, indice_y)
    lms[10] = _LM(0.5, 0.4)  # PIP medio
    lms[12] = _LM(0.5, medio_y)
    return HandData(handedness=handedness, score=0.95, landmarks=lms)


class TestModoPorMano(unittest.TestCase):
    def test_pulgar_mas_indice_con_medio_plegado_es_L(self):
        # L: pulgar e índice arriba, medio abajo (plegado)
        mano = make_hand(indice_y=0.2, medio_y=0.5, pulgar_extendido=True)
        self.assertEqual(gesture.mode_for_hand(mano), gesture.MODO_L)

    def test_mano_completa_todos_los_dedos_es_MC(self):
        # palma abierta: pulgar, índice y medio extendidos
        mano = make_hand(indice_y=0.2, medio_y=0.2, pulgar_extendido=True)
        self.assertEqual(gesture.mode_for_hand(mano), gesture.MODO_MANO_COMPLETA)

    def test_indice_y_medio_sin_pulgar_no_es_modo(self):
        # la antigua "V" (índice+medio sin pulgar) ya no es un modo
        mano = make_hand(indice_y=0.2, medio_y=0.2, pulgar_extendido=False)
        self.assertEqual(gesture.mode_for_hand(mano), gesture.MODO_NINGUNO)

    def test_ningun_dedo_no_es_modo(self):
        mano = make_hand(indice_y=0.5, medio_y=0.5, pulgar_extendido=False)
        self.assertEqual(gesture.mode_for_hand(mano), gesture.MODO_NINGUNO)

    def test_indice_solo_no_es_modo(self):
        mano = make_hand(indice_y=0.2, medio_y=0.5, pulgar_extendido=False)
        self.assertEqual(gesture.mode_for_hand(mano), gesture.MODO_NINGUNO)


class TestModoGlobal(unittest.TestCase):
    def test_dos_manos_coinciden_en_L(self):
        izq = make_hand(0.2, 0.5, True, "Left")
        der = make_hand(0.2, 0.5, True, "Right")
        modo, por_mano = gesture.mode_for_hands([izq, der])
        self.assertEqual(modo, gesture.MODO_L)
        self.assertEqual(por_mano, [gesture.MODO_L, gesture.MODO_L])

    def test_dos_manos_coinciden_en_mano_completa(self):
        izq = make_hand(0.2, 0.2, True, "Left")
        der = make_hand(0.2, 0.2, True, "Right")
        modo, por_mano = gesture.mode_for_hands([izq, der])
        self.assertEqual(modo, gesture.MODO_MANO_COMPLETA)
        self.assertEqual(por_mano, [gesture.MODO_MANO_COMPLETA] * 2)

    def test_manos_en_desacuerdo_no_hay_marco(self):
        izq = make_hand(0.2, 0.5, True, "Left")    # L
        der = make_hand(0.2, 0.2, True, "Right")   # MANO_COMPLETA
        modo, _ = gesture.mode_for_hands([izq, der])
        self.assertEqual(modo, gesture.MODO_NINGUNO)

    def test_una_sola_mano_no_hay_marco(self):
        der = make_hand(0.2, 0.5, True, "Right")
        modo, _ = gesture.mode_for_hands([der])
        self.assertEqual(modo, gesture.MODO_NINGUNO)


if __name__ == "__main__":
    unittest.main()
