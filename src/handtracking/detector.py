"""Detección de manos con MediaPipe Tasks API (HandLandmarker).

MediaPipe 1.0.0 eliminó la API legacy `mp.solutions.hands`; se usa la Tasks
API, que requiere un modelo externo `hand_landmarker.task` (descargado por
`tools/download_models.py`). El resultado expone, por mano, la lateralidad
(`Left`/`Right` con su score) y los 21 landmarks normalizados (x, y en [0,1]).
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import List, Optional, Sequence

import cv2
import mediapipe as mp
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision import RunningMode
from mediapipe.tasks.python.vision.hand_landmarker import (
    HandLandmarker,
    HandLandmarkerOptions,
    HandLandmarkerResult,
)

# Índices de landmarks relevantes (convención oficial de MediaPipe).
TIP_PULGAR = 4
MCP_PULGAR = 2
IP_PULGAR = 3
TIP_INDICE = 8
MCP_INDICE = 5
PIP_INDICE = 6
TIP_MEDIO = 12
PIP_MEDIO = 10

# Ruta por defecto del modelo relativa a la raíz del proyecto.
DEFAULT_MODEL = Path(__file__).resolve().parents[2] / "data" / "models" / "hand_landmarker.task"


@dataclasses.dataclass
class HandData:
    """Datos de una mano detectada en el frame actual."""

    handedness: str          # 'Left' o 'Right' (del punto de vista de MediaPipe)
    score: float             # confianza de la lateralidad (0..1)
    landmarks: Sequence      # 21 landmarks NormalizedLandmark (x, y en [0,1])

    def point(self, index: int) -> tuple:
        """Devuelve (x, y) normalizado del landmark `index`."""
        lm = self.landmarks[index]
        return (lm.x, lm.y)


class HandDetector:
    """Detección de manos por frame (modo IMAGE, síncrono).

    Uso::

        detector = HandDetector()
        hands = detector.process(frame_bgr)   # lista de HandData (puede ser vacía)
        detector.close()
    """

    def __init__(self, model_path: Path | str = DEFAULT_MODEL,
                 num_hands: int = 2, confidence: float = 0.5):
        model_path = Path(model_path)
        if not model_path.exists():
            raise FileNotFoundError(
                f"Modelo de manos no encontrado: {model_path}. "
                "Ejecuta: python tools/download_models.py"
            )
        options = HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=str(model_path)),
            running_mode=RunningMode.IMAGE,
            num_hands=num_hands,
            min_hand_detection_confidence=confidence,
            min_hand_presence_confidence=confidence,
            min_tracking_confidence=confidence,
        )
        self._landmarker = HandLandmarker.create_from_options(options)

    def process(self, frame_bgr) -> List[HandData]:
        """Detecta manos en un frame BGR y devuelve la lista de `HandData`."""
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result: HandLandmarkerResult = self._landmarker.detect(image)
        return self._to_hands(result)

    @staticmethod
    def _to_hands(result: HandLandmarkerResult) -> List[HandData]:
        hands: List[HandData] = []
        for i, landmarks in enumerate(result.hand_landmarks):
            category = result.handedness[i][0]
            hands.append(HandData(
                handedness=category.category_name,
                score=category.score,
                landmarks=landmarks,
            ))
        return hands

    def close(self) -> None:
        self._landmarker.close()

    def __enter__(self) -> "HandDetector":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
