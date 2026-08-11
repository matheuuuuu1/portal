"""Benchmark Fase 10: FPS y CPU del pipeline completo (cámara→manos→cielo→composición).

Mide cada etapa por separado y el ciclo completo, para saber dónde está el
cuello de botella frente al objetivo de 30 FPS a 720p (ADR-007). La CPU se
estima con `time.process_time()` (tiempo de CPU del proceso entre el tiempo de
pared), sin dependencias extra.

Uso:

    # Frames sintéticos (sin cámara, headless — útil para CI y para medir el
    # coste de CPU de cada etapa de forma determinista):
    python tools/benchmark_fase10.py

    # Con la cámara real y el marco que formen las manos (o sin marco):
    python tools/benchmark_fase10.py --camera 0

    # Comparar el render a resolución completa vs. reducida:
    python tools/benchmark_fase10.py --render-ancho 960 --render-alto 540
    python tools/benchmark_fase10.py --estetica-plano

Con `--camera`, la composición se hace SOLO cuando hay manos (como en la demo);
con frames sintéticos siempre se compone con un marco fijo para medir el peor
caso de cada etapa.
"""

from __future__ import annotations

import argparse
import statistics
import time

import cv2
import numpy as np
from skyfield.api import load

from app.capture import CameraCapture
from compositor.compositor import Compositor
from handtracking.pipeline import HandPipeline
from skyrender.estetica import ESTETICAS
from skyrender.render import SkyRenderer

ANCHO, ALTO = 1280, 720
QUAD = [(0.25, 0.25), (0.75, 0.25), (0.75, 0.75), (0.25, 0.75)]


def _frame_sintetico() -> np.ndarray:
    """Frame BGR con un patrón distinto en cada píxel (para no comprimir)."""
    y, x = np.mgrid[0:ALTO, 0:ANCHO]
    frame = np.zeros((ALTO, ANCHO, 3), dtype=np.uint8)
    frame[..., 0] = (x // 8) % 256
    frame[..., 1] = (y // 8) % 256
    frame[..., 2] = ((x + y) // 16) % 256
    return frame


class _Etapas:
    """Acumula los tiempos de cada etapa en nanosegundos para el informe."""

    def __init__(self):
        self.tiempos: dict[str, list[float]] = {}

    def registrar(self, etapa: str, inicio: float) -> None:
        self.tiempos.setdefault(etapa, []).append(
            (time.perf_counter() - inicio) * 1e6)   # µs

    def informe(self, n: int) -> str:
        lineas = ["\nEtapa                  media    mediana       p95        FPS",
                  "------------------------  -------  --------  --------  -------"]
        for etapa, ts in sorted(self.tiempos.items()):
            media = statistics.mean(ts)
            mediana = statistics.median(ts)
            p95 = sorted(ts)[int(len(ts) * 0.95) - 1]
            fps = 1e6 / media if media > 0 else 0.0
            lineas.append(f"{etapa:<24} {media:7.1f} {mediana:8.1f} {p95:9.1f} "
                          f"{fps:6.1f}")
        return "\n".join(lineas)


def run(args) -> int:
    renderer = SkyRenderer(ancho=args.render_ancho, alto=args.render_alto,
                           fov_deg=60.0,
                           estetica=("plano" if args.estetica_plano
                                     else "noche_profunda"))
    compositor = Compositor(ancho=ANCHO, alto=ALTO, borde_suave=2.0)
    pipeline = HandPipeline()
    ts = load.timescale()
    etapas = _Etapas()

    if args.camera is not None:
        fuente = CameraCapture(index=args.camera).open().__enter__()
    else:
        fuente = None
        frame_sintetico = _frame_sintetico()

    # Calienta cachés (skyfield, catálogo, modelo de manos, estética).
    for _ in range(args.warmup):
        frame = frame_sintetico if fuente is None else fuente.read()
        if frame is None:
            break
        pipeline.process(frame)
        renderer.render(ts.now(), 180.0, 45.0, etiquetas=True)

    duracion = (f"{args.soak_segundos:.0f} s (soak)"
                if args.soak_segundos else f"{args.frames} frames")
    print(f"Benchmark Fase 10 — {duracion} "
          f"({args.warmup} de calentamiento). "
          f"Cámara: {'real ' + str(args.camera) if fuente is not None else 'sintética'}. "
          f"Render: {renderer.ancho}x{renderer.alto} "
          f"(estética {renderer.estetica}).")

    cpu_ini = time.process_time()
    t0 = time.perf_counter()
    veces_compuesto = 0
    frames_hechos = 0
    ultimo_reporte = t0
    ultimo_frame = 0
    objetivo = (None if args.soak_segundos else args.frames)
    while True:
        if objetivo is not None and frames_hechos >= objetivo:
            break
        if args.soak_segundos and time.perf_counter() - t0 >= args.soak_segundos:
            break
        t = ts.now()
        inicio = time.perf_counter()
        frame = frame_sintetico if fuente is None else fuente.read()
        if frame is None:
            print("Aviso: la cámara dejó de entregar frames; se corta aquí.")
            break
        etapas.registrar("captura", inicio)

        inicio = time.perf_counter()
        hand = pipeline.process(frame)
        etapas.registrar("manos", inicio)

        inicio = time.perf_counter()
        cielo = renderer.render(t, 180.0, 45.0, etiquetas=True)
        etapas.registrar("render", inicio)

        # Con cámara solo se compone si hay marco (como la demo); con sintético
        # siempre, para medir el peor caso.
        if args.camera is not None:
            if hand.valid:
                inicio = time.perf_counter()
                compositor.compone(frame, cielo, hand.quad_smooth)
                etapas.registrar("composicion", inicio)
                veces_compuesto += 1
        else:
            inicio = time.perf_counter()
            compositor.compone(frame, cielo, QUAD)
            etapas.registrar("composicion", inicio)
            veces_compuesto += 1

        frames_hechos += 1
        # En modo soak, un informe parcial cada ~10 s para ver si el FPS se
        # degrada (fugas, acumulación de caché) o se mantiene estable.
        if args.soak_segundos:
            ahora = time.perf_counter()
            if ahora - ultimo_reporte >= 10.0:
                fps_ventana = ((frames_hechos - ultimo_frame)
                               / (ahora - ultimo_reporte))
                print(f"  [{ahora - t0:6.1f} s] {frames_hechos} frames -> "
                      f"{fps_ventana:5.1f} FPS")
                ultimo_reporte = ahora
                ultimo_frame = frames_hechos

    t_total = time.perf_counter() - t0
    cpu_uso = (time.process_time() - cpu_ini) / t_total if t_total > 0 else 0.0

    n = len(etapas.tiempos.get("render", []))
    print(etapas.informe(n))
    print(f"\nCiclo completo: {t_total / max(1, n) * 1e3:.1f} ms/frame -> "
          f"{n / t_total:.1f} FPS  (CPU del proceso: {cpu_uso * 100:.0f}%)")
    print(f"Composiciones con marco: {veces_compuesto}/{n}")

    if fuente is not None:
        fuente.__exit__(None, None, None)
    pipeline.close()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark del pipeline completo (Fase 10)")
    parser.add_argument("--camera", type=int, default=None,
                        help="índice de la cámara real (si no, frames sintéticos)")
    parser.add_argument("--frames", type=int, default=300,
                        help="frames medidos (def. 300; se ignora con --soak)")
    parser.add_argument("--soak-segundos", type=float, default=0.0,
                        help="modo de resistencia: correr N segundos e "
                             "informar FPS cada ~10 s para ver degradación "
                             "(def. 0 = modo frames)")
    parser.add_argument("--warmup", type=int, default=30,
                        help="frames de calentamiento (def. 30)")
    parser.add_argument("--render-ancho", type=int, default=1280,
                        help="ancho del render del cielo (def. 1280)")
    parser.add_argument("--render-alto", type=int, default=720,
                        help="alto del render del cielo (def. 720)")
    parser.add_argument("--estetica-plano", action="store_true",
                        help="comparar sin estética (solo astros)")
    args = parser.parse_args()
    if (args.render_ancho != ANCHO or args.render_alto != ALTO) \
            and not (args.render_ancho <= ANCHO and args.render_alto <= ALTO):
        parser.error("el render reducido debe caber dentro del frame "
                     "(1280x720)")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())
