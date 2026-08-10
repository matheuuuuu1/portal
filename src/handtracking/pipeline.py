"""Pipeline de handtracking: detector + gesto + cuadrilátero + suavizado.

Es la puerta de entrada que usará `app` y `compositor`: dado un frame BGR,
devuelve las manos detectadas, el modo de gesto (ADR-004) y el cuadrilátero
del marco suavizado y validado.
"""

from __future__ import annotations

import dataclasses
from typing import List, Optional, Sequence, Tuple

from . import gesture, quadrilateral
from .detector import HandData, HandDetector
from .smoothing import QuadSmoother


@dataclasses.dataclass
class HandFrame:
    """Resultado del pipeline para un frame."""

    hands: List[HandData]
    modes: List[str]                 # modo por mano (L/MANO_COMPLETA/NINGUNO)
    mode: str                        # modo global del marco (gesture.MODO_*)
    quad: Optional[List[Tuple[float, float]]]             # esquinas brutas, normalizadas
    quad_smooth: Optional[List[Tuple[float, float]]]      # esquinas suavizadas y válidas
    valid: bool                      # True si hay un marco utilizable este frame


class HandPipeline:
    """Une detección, gesto, cuadrilátero y suavizado en una sola llamada."""

    def __init__(self, quad_alpha: float = 0.45, debounce_frames: int = 3,
                 **detector_kwargs):
        self.detector = HandDetector(**detector_kwargs)
        self.smoother = QuadSmoother(alpha=quad_alpha)
        self._debounce_frames = max(1, debounce_frames)
        self._last_mode = gesture.MODO_NINGUNO
        self._mode_streak = 0

    def _confirm_mode(self, raw_mode: str) -> str:
        """Estabiliza el modo: solo cambia si se mantiene N frames seguidos.

        Elimina los parpadeos del modo al pasar de L a MANO_COMPLETA o al
        perder/recuperar las manos (feedback del usuario: la L "trabada").
        """
        if raw_mode == self._last_mode:
            self._mode_streak += 1
        else:
            self._last_mode = raw_mode
            self._mode_streak = 1
        if self._mode_streak >= self._debounce_frames:
            return raw_mode
        return gesture.MODO_NINGUNO

    def process(self, frame_bgr) -> HandFrame:
        hands = self.detector.process(frame_bgr)
        raw_mode, modes = gesture.mode_for_hands(hands)
        mode = self._confirm_mode(raw_mode)
        quad = quadrilateral.build_quad(hands, mode)
        valid = quadrilateral.validate_quad(quad)

        if valid:
            quad_smooth = self.smoother.update(quad)
            # El filtro puede arrastrar el marco a un área mínima; si el suave
            # deja de cumplir, se conserva el bruto.
            if not quadrilateral.validate_quad(quad_smooth):
                quad_smooth = quad
        else:
            self.smoother.reset()
            quad_smooth = None

        return HandFrame(hands=hands, modes=modes, mode=mode, quad=quad,
                         quad_smooth=quad_smooth, valid=valid)

    def close(self) -> None:
        self.detector.close()
