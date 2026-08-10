"""Suavizado temporal de landmarks (filtro exponencial / EMA).

Reduce el temblor de la detección de MediaPipe. Se aplica a las 4 esquinas del
marco: 8 valores (x, y por esquina). Se resetea cuando no hay marco para que el
filtro no "arrastre" posiciones antiguas al reaparecer las manos.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple


class QuadSmoother:
    """Suavizado exponencial para una secuencia de puntos (marco)."""

    def __init__(self, alpha: float = 0.45):
        if not 0.0 < alpha <= 1.0:
            raise ValueError("alpha debe estar en (0, 1]")
        self.alpha = alpha
        self._value: Optional[List[float]] = None

    def update(self, points: Sequence[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """Avanza un frame y devuelve los puntos suavizados (misma forma)."""
        flat = [c for p in points for c in p]
        if self._value is None:
            self._value = list(flat)
        else:
            a = self.alpha
            self._value = [a * v + (1.0 - a) * old for v, old in zip(flat, self._value)]
        return [(self._value[i], self._value[i + 1]) for i in range(0, len(self._value), 2)]

    def reset(self) -> None:
        self._value = None
