"""Construcción y validación del cuadrilátero del marco.

Cada mano aporta dos dedos (dos esquinas de su lado). En ambos modos de gesto
(ADR-004) las esquinas son siempre el pulgar (4) y el índice (8): el modo solo
cambia qué se muestra DENTRO del marco, no la forma del marco.

Con los 4 puntos se ordenan las esquinas (TL, TR, BR, BL) con el método
clásico de imutils (suma/resta de coordenadas), que asume un rectángulo
aproximadamente alineado con la imagen — es el caso del marco de manos.
"""

from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from . import gesture
from .detector import HandData, TIP_INDICE, TIP_PULGAR

# Par de landmarks que aporta cada mano como esquinas de su lado (ADR-004).
QUAD_POINTS = (TIP_PULGAR, TIP_INDICE)

# Área mínima (en fracción del área del frame, coordenadas normalizadas [0,1])
# para que el marco sea válido. Rechaza cuadriláteros degenerados (p. ej. manos
# demasiado juntas o marco casi colapsado).
MIN_AREA = 0.02


def build_quad(hands: List[HandData], mode: str) -> Optional[List[Tuple[float, float]]]:
    """Construye el cuadrilátero normalizado desde las dos manos.

    Devuelve una lista de 4 puntos (x, y) en coordenadas normalizadas [0,1]
    ordenados TL, TR, BR, BL, o None si no hay dos manos o no hay un modo de
    marco activo.
    """
    if len(hands) != 2 or mode not in (gesture.MODO_L, gesture.MODO_MANO_COMPLETA):
        return None
    p1, p2 = QUAD_POINTS
    quad = [hands[0].point(p1), hands[0].point(p2),
            hands[1].point(p1), hands[1].point(p2)]
    return order_quad_points(quad)


def order_quad_points(points: Sequence[Tuple[float, float]]) -> List[Tuple[float, float]]:
    """Ordena 4 puntos como TL, TR, BR, BL (método de imutils)."""
    idx = list(range(4))
    s = [points[i][0] + points[i][1] for i in idx]
    tl_i = min(idx, key=lambda i: s[i])
    br_i = max(idx, key=lambda i: s[i])
    rest = [i for i in idx if i != tl_i and i != br_i]
    # TR tiene el diff (y - x) más negativo; BL el más positivo.
    d0 = points[rest[0]][1] - points[rest[0]][0]
    d1 = points[rest[1]][1] - points[rest[1]][0]
    tr_i, bl_i = (rest[0], rest[1]) if d0 < d1 else (rest[1], rest[0])
    return [points[tl_i], points[tr_i], points[br_i], points[bl_i]]


def polygon_area(points: Sequence[Tuple[float, float]]) -> float:
    """Área del polígono por la fórmula del shoelace (en unidades normalizadas)."""
    n = len(points)
    area = 0.0
    for i in range(n):
        x1, y1 = points[i]
        x2, y2 = points[(i + 1) % n]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def validate_quad(points: Optional[Sequence[Tuple[float, float]]],
                  min_area: float = MIN_AREA) -> bool:
    """True si el cuadrilátero es un marco válido (no degenerado)."""
    if not points or len(points) != 4:
        return False
    return polygon_area(points) >= min_area
