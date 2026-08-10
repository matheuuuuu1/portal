"""Fase 2 — Demo de detección de manos y marco.

Muestra en vivo: los landmarks de las manos detectadas, la lateralidad, el
cuadrilátero del marco (suavizado) y el modo de gesto (L/V, ver ADR-004).

Ejecutar (entorno activado):

    python -m handtracking.demo_hands

Salida: tecla q o ESC. Si falta el modelo, ejecuta primero:
    python tools/download_models.py
"""

import time

import cv2
import numpy as np

from app.capture import CameraCapture
from handtracking import gesture
from handtracking.pipeline import HandPipeline

WINDOW_NAME = "Portal al Cielo — Fase 2 (manos y marco)"

# Conexiones de la mano (pares de landmarks) para dibujar el esqueleto.
_HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
]

_MODE_COLOR = {
    gesture.MODO_L: (0, 255, 0),           # verde: sin nombres
    gesture.MODO_MANO_COMPLETA: (0, 200, 255),  # naranja: con nombres
}


def _to_pixels(points, w, h):
    return [(int(x * w), int(y * h)) for x, y in points]


def draw_hands(frame, hand_frame):
    h, w = frame.shape[:2]
    for hand in hand_frame.hands:
        pts = [(int(hand.landmarks[i].x * w), int(hand.landmarks[i].y * h)) for i in range(21)]
        # esqueleto
        for a, b in _HAND_CONNECTIONS:
            cv2.line(frame, pts[a], pts[b], (200, 200, 200), 1, cv2.LINE_AA)
        # nodos
        for p in pts:
            cv2.circle(frame, p, 3, (255, 255, 255), -1, cv2.LINE_AA)
        # etiqueta de lateralidad junto a la muñeca (landmark 0)
        label = f"{hand.handedness[0]} {hand.score:.2f}"
        cv2.putText(frame, label, (pts[0][0] - 10, pts[0][1] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1, cv2.LINE_AA)
        # estado de dedos por mano: P/I/M = pulgar/índice/medio (1 = extendido)
        s = gesture.finger_states(hand)
        dedos = (f"P{int(s[gesture.DEDO_PULGAR])} "
                 f"I{int(s[gesture.DEDO_INDICE])} "
                 f"M{int(s[gesture.DEDO_MEDIO])}")
        cv2.putText(frame, dedos, (pts[0][0] - 10, pts[0][1] + 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1, cv2.LINE_AA)

    # marco suavizado
    if hand_frame.valid and hand_frame.quad_smooth:
        color = _MODE_COLOR.get(hand_frame.mode, (0, 255, 0))
        quad_px = _to_pixels(hand_frame.quad_smooth, w, h)
        # OpenCV 5.0 exige un array numpy int32 para polylines.
        quad_np = np.array(quad_px, dtype=np.int32).reshape(-1, 1, 2)
        cv2.polylines(frame, [quad_np], isClosed=True, color=color,
                      thickness=3, lineType=cv2.LINE_AA)
        for p in quad_px:
            cv2.circle(frame, p, 6, color, -1, cv2.LINE_AA)


def run():
    with CameraCapture().open() as cam:
        pipeline = HandPipeline()
        tick = fps_counter()
        cv2.namedWindow(WINDOW_NAME)
        try:
            while True:
                frame = cam.read()
                if frame is None:
                    print("Aviso: la cámara dejó de entregar frames.")
                    break

                hand_frame = pipeline.process(frame)
                draw_hands(frame, hand_frame)

                fps = tick(time.perf_counter())
                cv2.putText(frame, f"FPS: {fps:5.1f}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 0), 2, cv2.LINE_AA)
                modo_txt = (f"MODO: {hand_frame.mode}  [{hand_frame.modes}]"
                            if hand_frame.mode != gesture.MODO_NINGUNO else "MODO: sin marco")
                cv2.putText(frame, modo_txt, (10, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 0), 1, cv2.LINE_AA)

                cv2.imshow(WINDOW_NAME, frame)
                if cv2.waitKey(1) & 0xFF in (ord("q"), 27):
                    break
        finally:
            cv2.destroyAllWindows()
            pipeline.close()


def fps_counter():
    window = []
    max_window = 30

    def tick(now):
        window.append(now)
        if len(window) > max_window:
            window.pop(0)
        if len(window) < 2:
            return 0.0
        dt = window[-1] - window[0]
        return (len(window) - 1) / dt if dt > 0 else 0.0

    return tick


if __name__ == "__main__":
    run()
