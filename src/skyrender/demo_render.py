"""Demo de la Fase 7: ventana con el cielo renderizado en tiempo real.

Uso::

    python -m skyrender.demo_render [--fov GRADOS] [--rumbo GRADOS]
                                   [--inclinacion GRADOS] [--lat L] [--lon L]
                                   [--brillo FACTOR]

Teclas dentro de la ventana:

- Flechas: ← → cambian el rumbo, ↑ ↓ cambian la inclinación.
- +/-: abren/cierran el campo de visión.
- [ / ]: bajan/suben el factor de brillo de las estrellas (0.1 a 3.0).
- r: devuelve la vista al rumbo/inclinación iniciales.
- q / ESC: salir.

El instante se toma del reloj del sistema, así que el cielo corresponde al
cielo real de ese momento y lugar. El contador de FPS se muestra arriba.
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime, timezone

import cv2
from skyfield.api import load

from .astro import Ubicacion, cargar_ubicacion
from .render import SkyRenderer


def main() -> int:
    parser = argparse.ArgumentParser(description="Demo de render del cielo (F7)")
    parser.add_argument("--fov", type=float, default=60.0,
                        help="campo de visión horizontal en grados (def. 60)")
    parser.add_argument("--rumbo", type=float, default=180.0,
                        help="azimut inicial en grados (def. 180 = sur)")
    parser.add_argument("--inclinacion", type=float, default=45.0,
                        help="altitud inicial en grados (def. 45)")
    parser.add_argument("--brillo", type=float, default=2.5,
                        help="factor de brillo de las estrellas (def. 2.5)")
    parser.add_argument("--lat", type=float, help="latitud (si no, la guardada)")
    parser.add_argument("--lon", type=float, help="longitud (si no, la guardada)")
    parser.add_argument("--sin-ventana", action="store_true",
                        help="renderiza N frames y mide el tiempo (para tests)")
    parser.add_argument("--frames", type=int, default=120,
                        help="frames a renderizar en modo --sin-ventana")
    args = parser.parse_args()

    ubicacion = cargar_ubicacion()
    if args.lat is not None and args.lon is not None:
        lat, lon = args.lat, args.lon
    elif ubicacion is not None:
        lat, lon = ubicacion.lat, ubicacion.lon
    else:
        print("Falta la ubicación: pasa --lat/--lon o crea data/ubicacion.json")
        return 2

    renderer = SkyRenderer(ancho=1280, alto=720, fov_deg=args.fov)
    renderer.ubicacion = Ubicacion(lat=lat, lon=lon, nombre="demo")

    ts = load.timescale()

    if args.sin_ventana:
        t = ts.now()
        inicio = time.perf_counter()
        for _ in range(args.frames):
            renderer.render(t, args.rumbo, args.inclinacion)
        total = time.perf_counter() - inicio
        fps = args.frames / total
        print(f"{args.frames} frames a {renderer.ancho}x{renderer.alto} "
              f"en {total:.2f}s -> {fps:.1f} FPS")
        return 0

    print("Fase 7 — Render del cielo. Flechas: rumbo/inclinación. "
          "+/-: FOV. [ / ]: brillo. r: reiniciar. q/ESC: salir.")
    rumbo, inclinacion, fov = args.rumbo, args.inclinacion, args.fov
    brillo = args.brillo
    renderer.brillo_factor = brillo
    base = (rumbo, inclinacion)
    t_prev = time.perf_counter()

    while True:
        t = ts.now()
        if fov != renderer.fov_deg:
            renderer = SkyRenderer(ancho=1280, alto=720, fov_deg=fov)
            renderer.ubicacion = Ubicacion(lat=lat, lon=lon, nombre="demo")
            renderer.brillo_factor = brillo
        img = renderer.render(t, rumbo % 360.0, inclinacion)

        ahora = time.perf_counter()
        fps = 1.0 / max(1e-6, ahora - t_prev)
        t_prev = ahora
        cv2.putText(img, f"{fps:4.1f} fps | rumbo {rumbo:6.1f}  "
                        f"incl {inclinacion:5.1f}  fov {fov:4.1f}  "
                        f"brillo {brillo:4.2f}",
                    (12, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                    (0, 255, 0), 1, cv2.LINE_AA)
        cv2.imshow("Portal al Cielo - Fase 7", img)

        tecla = cv2.waitKey(1) & 0xFF
        if tecla in (ord("q"), 27):
            break
        elif tecla == 81 or tecla == ord("a"):    # flecha izquierda
            rumbo -= 5.0
        elif tecla == 83 or tecla == ord("d"):    # flecha derecha
            rumbo += 5.0
        elif tecla == 82 or tecla == ord("w"):    # flecha arriba
            inclinacion = min(90.0, inclinacion + 5.0)
        elif tecla == 84 or tecla == ord("s"):    # flecha abajo
            inclinacion = max(-90.0, inclinacion - 5.0)
        elif tecla == ord("+"):
            fov = min(120.0, fov + 5.0)
        elif tecla == ord("-"):
            fov = max(20.0, fov - 5.0)
        elif tecla == ord("["):
            brillo = max(0.1, round(brillo - 0.1, 2))
            renderer.brillo_factor = brillo
        elif tecla == ord("]"):
            brillo = min(3.0, round(brillo + 0.1, 2))
            renderer.brillo_factor = brillo
        elif tecla == ord("r"):
            rumbo, inclinacion = base

    cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
