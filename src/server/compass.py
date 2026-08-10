"""Estado compartido de la orientación del celular (brújula).

Es la única fuente de verdad de la orientación (ARQUITECTURA). El servidor
actualiza este estado desde el WebSocket del celular y `skyrender` lo lee en
cada frame. El acceso es seguro entre hilos (lock) porque el servidor aiohttp
y el bucle principal de la app corren en hilos distintos.
"""

from __future__ import annotations

import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# Si el último mensaje es más viejo que esto, la orientación se considera
# obsoleta (el celular se desconectó).
STALE_TIMEOUT = 2.0

# Dónde se guarda el offset de calibración entre sesiones (Fase 5).
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
RUTA_CALIBRACION = DATA_DIR / "calibracion.json"


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


@dataclass
class Calibracion:
    """Petición de calibración: el rumbo actual del celular es el norte (0)."""
    rumbo: float


def parse_mensaje(datos) -> Optional[object]:
    """Valida un mensaje del protocolo celular->laptop.

    Tipos soportados (ARQUITECTURA, sección 4)::

        {"tipo": "orientacion", "rumbo": 212.3, "inclinacion": 8.5,
         "roll": 0.0, "ts": 1720000000.123}   # lectura normal

        {"tipo": "calibrar", "rumbo": 5.3}    # el rumbo actual es el norte

    Devuelve una Orientacion, una Calibracion o None si no es válido.
    """
    if not isinstance(datos, dict):
        return None
    tipo = datos.get("tipo")
    if tipo == "calibrar":
        try:
            rumbo = float(datos["rumbo"])
        except (KeyError, TypeError, ValueError):
            return None
        if not 0.0 <= rumbo < 360.0:
            return None
        return Calibracion(rumbo=rumbo)
    if tipo != "orientacion":
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

    def __init__(self, ruta_calibracion: Path | None = RUTA_CALIBRACION) -> None:
        self._lock = threading.Lock()
        self._cruda = Orientacion()  # última lectura del celular, sin offset
        self._orientacion = Orientacion()
        self._offset_rumbo = 0.0
        self._ruta_calibracion = ruta_calibracion
        self._cargar_offset()

    # --- internos de offset ----------------------------------------------

    def _aplicar_offset(self, o: Orientacion) -> Orientacion:
        return Orientacion(
            rumbo=(o.rumbo - self._offset_rumbo) % 360,
            inclinacion=o.inclinacion,
            roll=o.roll,
            ts=o.ts,
        )

    def _cargar_offset(self) -> None:
        if not self._ruta_calibracion or not self._ruta_calibracion.exists():
            return
        try:
            datos = json.loads(self._ruta_calibracion.read_text("utf-8"))
            self._offset_rumbo = float(datos["offset"]) % 360
        except (OSError, ValueError, KeyError, TypeError):
            self._offset_rumbo = 0.0

    def _guardar_offset(self) -> None:
        if not self._ruta_calibracion:
            return
        try:
            self._ruta_calibracion.parent.mkdir(parents=True, exist_ok=True)
            self._ruta_calibracion.write_text(
                json.dumps({"offset": round(self._offset_rumbo, 2),
                            "ts": round(time.time(), 2)}),
                encoding="utf-8")
        except OSError:
            pass  # la calibración queda en memoria aunque no se persista

    # --- API pública -----------------------------------------------------

    def update(self, orientacion: Orientacion) -> None:
        """Guarda una lectura aplicando el offset de calibración."""
        with self._lock:
            self._cruda = orientacion
            self._orientacion = self._aplicar_offset(orientacion)

    def calibrar(self, rumbo: float) -> float:
        """Declara que el rumbo actual del celular es el norte (0)."""
        offset = rumbo % 360
        with self._lock:
            self._offset_rumbo = offset
            self._orientacion = self._aplicar_offset(self._cruda)
        self._guardar_offset()
        return offset

    @property
    def calibrado(self) -> bool:
        """True si hay un offset de calibración aplicado."""
        return self._offset_rumbo != 0.0

    def get(self) -> Orientacion:
        with self._lock:
            return Orientacion(**self._orientacion.to_dict())

    @property
    def fresh(self) -> bool:
        """True si la última lectura es reciente (el celular está conectado)."""
        return (time.time() - self.get().ts) < STALE_TIMEOUT
