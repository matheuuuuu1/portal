"""Captura de cámara web con normalización del frame a 720p.

La cámara puede entregar una resolución nativa distinta de la objetivo
(1280x720); este módulo redimensiona cada frame al tamaño objetivo para que el
resto del pipeline (handtracking y compositor) siempre reciba imágenes de las
mismas dimensiones. Objetivo de rendimiento: 720p a 30 FPS (ADR-007).
"""

import cv2

# Resolución objetivo del pipeline completo (ADR-007).
OBJ_WIDTH = 1280
OBJ_HEIGHT = 720
OBJ_FPS = 30


class CameraCapture:
    """Abre la cámara web y entrega frames BGR normalizados a 720p.

    Uso::

        with CameraCapture().open() as cam:
            frame = cam.read()   # BGR, 1280x720 siempre

    Si la cámara no soporta 1280x720 nativo, se redimensiona en cada read().

    Sobre el backend: medido en el hardware objetivo, DirectShow (CAP_DSHOW)
    entrega ~10 fps mientras que el backend por defecto entrega ~30 fps a 720p
    (ver PROGRESO.md, Fase 1). Por eso NO se fuerza DSHOW; se usa el backend
    por defecto salvo que se indique lo contrario.
    """

    def __init__(self, index=0, width=OBJ_WIDTH, height=OBJ_HEIGHT, fps=OBJ_FPS,
                 backend=None):
        self.index = index
        self.width = width
        self.height = height
        self.fps = fps
        self.backend = backend  # None = cv2.CAP_ANY (recomendado)
        self._cap = None
        self.native_size = None  # (w, h) real que la cámara aceptó

    def open(self):
        """Abre la cámara y verifica que entrega frames."""
        if self.backend is None:
            self._cap = cv2.VideoCapture(self.index)
        else:
            self._cap = cv2.VideoCapture(self.index, self.backend)
        if not self._cap.isOpened():
            raise RuntimeError(
                f"No se pudo abrir la cámara {self.index}. "
                "Revisa que esté disponible y no usada por otra aplicación."
            )
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self._cap.set(cv2.CAP_PROP_FPS, self.fps)

        ok, frame = self._cap.read()  # fuerza la apertura real del sensor
        if not ok or frame is None:
            self.release()
            raise RuntimeError(f"La cámara {self.index} abrió pero no entrega frames.")
        self.native_size = (frame.shape[1], frame.shape[0])
        return self

    @property
    def needs_resize(self) -> bool:
        """True si la resolución nativa difiere del objetivo."""
        return self.native_size is not None and self.native_size != (self.width, self.height)

    def read(self):
        """Devuelve el siguiente frame BGR a `(width, height)`, o None al fallar."""
        ok, frame = self._cap.read()
        if not ok or frame is None:
            return None
        if frame.shape[1] != self.width or frame.shape[0] != self.height:
            frame = cv2.resize(frame, (self.width, self.height))
        return frame

    def release(self):
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.release()
        return False
