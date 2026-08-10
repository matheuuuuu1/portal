"""Módulo server: brújula del celular (aiohttp + WebSocket).

Sirve la página estática en `/` y recibe en `/ws` los mensajes de orientación
{rumbo, inclinacion, roll, ts} del celular a 30-60 Hz (ADR-001). Plan A:
HTTPS con certificado auto-firmado. Plan B: HTTP vía adb reverse.
"""
