"""Estado compartido de la orientación del celular (brújula).

Es la única fuente de verdad de la orientación (ARQUITECTURA). El servidor
actualiza este estado desde el WebSocket del celular y `skyrender` lo lee en
cada frame. El acceso es seguro entre hilos (lock) porque el servidor aiohttp
y el bucle principal de la app corren en hilos distintos.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Optional

# Si el último mensaje es más viejo que esto, la orientación se considera
# obsoleta (el celular se desconectó).
STALE_TIMEOUT = 2.0


@dataclass
class Orientacion:
    """Lectura procesada del celular.

    - rumbo: 0-360 grados, azimut magnético (0 = norte), ya con el offset de
      calibración aplicado.
    - inclinacion: -90 a +90, 0 = horizontal, +90 = cénit.
    - roll: giro del celular (recibido; su uso en el cielo es opcional).
    - ts: marca de tiempo del mensaje (epoch, segundos).
    """

    rumbo: float = 0.0
    inclinacion: float = 0.0
    roll: float = 0.0
    ts: float = 0.0

    def to_dict(self) -> dict:
        return {"rumbo": self.rumbo, "inclinacion": self.inclinacion,
                "roll": self.roll, "ts": self.ts}


def parse_mensaje(datos) -> Optional[Orientacion]:
    """Valida un mensaje del protocolo celular->laptop.

    Formato (ARQUITECTURA, sección 4)::

        {"tipo": "orientacion", "rumbo": 212.3, "inclinacion": 8.5,
         "roll": 0.0, "ts": 1720000000.123}

    Devuelve None si el mensaje no es válido.
    """
    if not isinstance(datos, dict) or datos.get("tipo") != "orientacion":
        return None
    try:
        rumbo = float(datos["rumbo"])
        inclinacion = float(datos["inclinacion"])
        roll = float(datos["roll"])
        ts = float(datos["ts"])
    except (KeyError, TypeError, ValueError):
        return None
    if not 0.0 <= rumbo < 360.0:
        return None
    if not -90.0 <= inclinacion <= 90.0:
        return None
    if not -180.0 <= roll <= 180.0:
        return None
    if ts <= 0:
        return None
    return Orientacion(rumbo=rumbo, inclinacion=inclinacion, roll=roll, ts=ts)


class CompassState:
    """Estado en memoria de la última orientación, con corrección de rumbo."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._orientacion = Orientacion()
        self._offset_rumbo = 0.0  # calibración (Fase 5)

    def update(self, orientacion: Orientacion) -> None:
        """Guarda una lectura aplicando el offset de calibración."""
        with self._lock:
            self._orientacion = Orientacion(
                rumbo=(orientacion.rumbo - self._offset_rumbo) % 360,
                inclinacion=orientacion.inclinacion,
                roll=orientacion.roll,
                ts=orientacion.ts,
            )

    def get(self) -> Orientacion:
        with self._lock:
            return Orientacion(**self._orientacion.to_dict())

    @property
    def fresh(self) -> bool:
        """True si la última lectura es reciente (el celular está conectado)."""
        return (time.time() - self.get().ts) < STALE_TIMEOUT
