"""Selección del modo de gesto (ADR-004, actualizado y validado por el usuario).

El marco lo forman dos manos; cada mano aporta dos dedos (pulgar e índice) que
definen las dos esquinas de su lado. El modo cambia qué se muestra DENTRO del
marco:

- Modo L (pulgar + índice extendidos, medio PLEGADO): constelaciones y
  planetas SIN nombres.
- Modo MANO_COMPLETA (pulgar + índice + medio extendidos, palma abierta):
  los mismos astros, pero los más importantes CON su nombre.

El usuario validó esta interpretación el 2026-08-10, sustituyendo el antiguo
modo V (índice + medio), que resultaba incómodo de formar.

Heurística geométrica:
- Índice/medio extendidos: su extremo está más arriba que su articulación PIP
  (en la imagen, el eje y crece hacia abajo), con un margen.
- Pulgar extendido: su extremo (4) está más lejos del MCP (2) que la
  articulación intermedia (3), por un factor. Mide distancia en el plano de la
  imagen, robusto a la rotación (en la "L" el pulgar apunta lateralmente).
"""

from __future__ import annotations

import math
from typing import List, Tuple

from .detector import (
    HandData,
    IP_PULGAR,
    MCP_PULGAR,
    PIP_INDICE,
    PIP_MEDIO,
    TIP_INDICE,
    TIP_MEDIO,
    TIP_PULGAR,
)

MODO_L = "L"
MODO_MANO_COMPLETA = "MANO_COMPLETA"
MODO_NINGUNO = "NINGUNO"

# Margen (en coordenadas normalizadas) para declarar índice/medio extendidos.
# 0.035: tolerante al temblor pero lo bastante para distinguir plegado/extendido.
_EXTENSION_MARGIN = 0.035

# Factor del pulgar: un poco más sensible que antes (1.10) para que la "L" se
# detecte con más frecuencia (feedback del usuario: la L costaba estabilizarse).
_THUMB_FACTOR = 1.10

DEDO_PULGAR = "pulgar"
DEDO_INDICE = "indice"
DEDO_MEDIO = "medio"


def _dist(lm, a: int, b: int) -> float:
    return math.hypot(lm[a].x - lm[b].x, lm[a].y - lm[b].y)


def _is_extended_by_y(lm, tip: int, joint: int, margin: float = _EXTENSION_MARGIN) -> bool:
    """Índice/medio están extendidos si su extremo está claramente más arriba
    que su articulación PIP (en la imagen, el eje y crece hacia abajo)."""
    return lm[tip].y < lm[joint].y - margin


def _is_thumb_extended(lm, factor: float = _THUMB_FACTOR) -> bool:
    return _dist(lm, TIP_PULGAR, MCP_PULGAR) > factor * _dist(lm, IP_PULGAR, MCP_PULGAR)


def finger_states(hand: HandData, margin: float = _EXTENSION_MARGIN) -> dict:
    """Devuelve {dedo: bool} con los dedos extendidos de una mano."""
    lm = hand.landmarks
    return {
        DEDO_PULGAR: _is_thumb_extended(lm),
        DEDO_INDICE: _is_extended_by_y(lm, TIP_INDICE, PIP_INDICE, margin),
        DEDO_MEDIO: _is_extended_by_y(lm, TIP_MEDIO, PIP_MEDIO, margin),
    }


def mode_for_hand(hand: HandData, margin: float = _EXTENSION_MARGIN) -> str:
    """Modo que aporta una sola mano (L, MANO_COMPLETA o NINGUNO).

    Reglas (ADR-004 validado por el usuario):
    - MANO_COMPLETA: pulgar, índice y medio extendidos (palma abierta).
    - L: pulgar e índice extendidos y medio PLEGADO (se distingue de la mano
      completa por el estado del medio).
    """
    s = finger_states(hand, margin)
    if s[DEDO_PULGAR] and s[DEDO_INDICE] and s[DEDO_MEDIO]:
        return MODO_MANO_COMPLETA
    if s[DEDO_PULGAR] and s[DEDO_INDICE] and not s[DEDO_MEDIO]:
        return MODO_L
    return MODO_NINGUNO


def mode_for_hands(hands: List[HandData]) -> Tuple[str, List[str]]:
    """Modo global del marco.

    Solo hay marco cuando hay exactamente dos manos y ambas coinciden en el
    mismo modo (L o MANO_COMPLETA). Si las manos no coinciden, o falta alguna,
    el modo es NINGUNO y el marco no debe mostrarse.

    Devuelve (modo, modos_por_mano).
    """
    per_hand = [mode_for_hand(h) for h in hands]
    if len(per_hand) == 2 and per_hand[0] == per_hand[1] and per_hand[0] != MODO_NINGUNO:
        return per_hand[0], per_hand
    return MODO_NINGUNO, per_hand
