"""Fase 1 — Demo de captura de cámara.

Muestra el feed a 720p con un contador de FPS en pantalla.

Ejecutar (desde la raíz del proyecto, con el entorno activado):

    python -m app.demo_capture        # paquete instalado (pip install -e .)
    python src/app/demo_capture.py    # equivalente directo

Salida: tecla q o ESC. Muestra también la resolución nativa de la cámara.
"""

import time

import cv2

from app.capture import CameraCapture, OBJ_HEIGHT, OBJ_WIDTH

WINDOW_NAME = "Portal al Cielo — Fase 1 (captura)"


def fps_counter():
    """Devuelve un callable que acumula y devuelve el FPS medio cada ~30 frames."""
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


def run():
    with CameraCapture().open() as cam:
        tick = fps_counter()
        cv2.namedWindow(WINDOW_NAME)
        frames = 0
        start = time.perf_counter()
        try:
            while True:
                frame = cam.read()
                if frame is None:
                    print("Aviso: la cámara dejó de entregar frames.")
                    break

                now = time.perf_counter()
                fps = tick(now)

                cv2.putText(
                    frame,
                    f"FPS: {fps:5.1f}",
                    (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    1.0,
                    (0, 255, 0),
                    2,
                    cv2.LINE_AA,
                )
                cv2.putText(
                    frame,
                    f"nativa: {cam.native_size[0]}x{cam.native_size[1]}",
                    (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (200, 200, 0),
                    1,
                    cv2.LINE_AA,
                )
                cv2.imshow(WINDOW_NAME, frame)

                frames += 1
                if cv2.waitKey(1) & 0xFF in (ord("q"), 27):  # q o ESC
                    break
        finally:
            cv2.destroyAllWindows()
            elapsed = time.perf_counter() - start
            print(f"Captura cerrada. {frames} frames en {elapsed:.1f}s "
                  f"({frames / elapsed:.1f} fps medios si no hubo pausas).")


if __name__ == "__main__":
    run()
