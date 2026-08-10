"""Módulo server: brújula del celular (aiohttp + WebSocket).

Sirve la página estática en `/` y recibe en `/ws` los mensajes de orientación
{rumbo, inclinacion, roll, ts} del celular a 30-60 Hz (ADR-001). Plan A:
HTTPS con certificado auto-firmado. Plan B: HTTP vía adb reverse (Fase 4).
"""

from .compass import Calibracion, CompassState, Orientacion, parse_mensaje
from .web import BrújulaServer, iniciar_servidor

__all__ = ["Calibracion", "CompassState", "Orientacion", "parse_mensaje",
           "BrújulaServer", "iniciar_servidor"]
