"""Fase 8/9 — Demo de composición: cámara + manos + cielo dentro del marco.

Une las tres piezas ya validadas: la cámara real (`app.capture`), la
detección del marco con las manos (`handtracking.pipeline`) y el cielo
renderizado (`skyrender.render.SkyRenderer`), y muestra el resultado
compuesto en una ventana con contador de FPS.

La orientación del cielo se simula por teclado por defecto (flechas). Si se
pasa `--brujula URL`, la demo lee el rumbo/inclinación del servidor de la
brújula (que puede correr en paralelo con `python -m server`) vía `/estado`;
mientras haya datos frescos, gana la brújula.

Ejecutar (entorno activado, desde la raíz):

    python -m compositor.demo_compositor
    python -m compositor.demo_compositor --brujula https://localhost:8080

El servidor es solo TLS, así que la URL debe ser **https://** (con `http://`
la conexión se rechaza en silencio).

Teclas dentro de la ventana:

- ←/a →/d: rumbo.  ↑/w ↓/s: inclinación.
- [ / ]: brillo de las estrellas.
- n: modo de etiquetas — auto (según el gesto: L sin nombres, MANO_COMPLETA
  con nombres; por defecto) → siempre sí → siempre no.
- e: cambiar la estética del cielo (plano / noche profunda).
- m: cambiar el modo del marco (ventana recorta el cielo anclado /
  completo comprime todo el FOV en el marco).
- c: mostrar/ocultar el medidor (rumbo y altitud exactos bajo el cursor).
- r: devolver el rumbo/inclinación a los iniciales.
- q / ESC: salir.

Fase 9: las etiquetas siguen al gesto — el modo L muestra el cielo sin
nombres y el modo MANO_COMPLETA con los nombres de los astros más
importantes (`handtracking.gesture.etiquetas_segun_gesto`).
"""

from __future__ import annotations

import argparse
import json
import ssl
import threading
import time
import urllib.request

import cv2
import numpy as np
from skyfield.api import load

from app.capture import CameraCapture
from compositor.compositor import Compositor
from handtracking.gesture import etiquetas_segun_gesto
from handtracking.pipeline import HandPipeline
from skyrender.astro import Ubicacion, cargar_ubicacion
from skyrender.estetica import ESTETICAS
from skyrender.render import SkyRenderer

WINDOW_NAME = "Portal al Cielo — Fase 8 (composición)"


def fps_counter():
    """Callable que devuelve el FPS medio de la ventana de últimos 30 frames."""
    ventana = []
    max_window = 30

    def tick(ahora):
        ventana.append(ahora)
        if len(ventana) > max_window:
            ventana.pop(0)
        if len(ventana) < 2:
            return 0.0
        dt = ventana[-1] - ventana[0]
        return (len(ventana) - 1) / dt if dt > 0 else 0.0

    return tick


_COLOR_MEDIDOR = (255, 255, 0)          # cian, BGR


def _dibujar_medidor(img: np.ndarray, x: int, y: int,
                     az: float, alt: float) -> None:
    """Cruz a lo ancho de la ventana + lectura del punto bajo el cursor.

    Como la regla de un editor de imágenes: las líneas señalan el punto y la
    caja de arriba a la derecha muestra el rumbo y la altitud del cielo que se
    ve exactamente en ese píxel (`SkyRenderer.altaz_del_pixel`).
    """
    color = _COLOR_MEDIDOR
    cv2.line(img, (x, 0), (x, img.shape[0] - 1), color, 1, cv2.LINE_AA)
    cv2.line(img, (0, y), (img.shape[1] - 1, y), color, 1, cv2.LINE_AA)
    cv2.circle(img, (x, y), 4, color, 1, cv2.LINE_AA)
    texto = f"rumbo {az:6.1f}°   alt {alt:+6.1f}°"
    (tw, th), _ = cv2.getTextSize(texto, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 1)
    x0 = img.shape[1] - tw - 18
    y0 = 14
    cv2.rectangle(img, (x0 - 8, y0 - 4), (x0 + tw + 8, y0 + th + 8),
                  (15, 15, 25), -1)
    cv2.putText(img, texto, (x0, y0 + th), cv2.FONT_HERSHEY_SIMPLEX, 0.55,
                color, 1, cv2.LINE_AA)


class CompassReader(threading.Thread):
    """Lee `/estado` del servidor de la brújula en un hilo (sin bloquear).

    Solo consume lecturas `fresh` del servidor. Si no hay servidor o los datos
    envejecen, `orientacion()` devuelve None y la demo vuelve al teclado.
    """

    def __init__(self, url: str):
        super().__init__(daemon=True)
        self.url = url.rstrip("/")
        self._estado = None
        self._ts = 0.0
        self._stop = False
        self._contexto = None
        if self.url.startswith("https"):
            # Certificado auto-firmado local del Plan A: la demo no lo verifica.
            self._contexto = ssl.create_default_context()
            self._contexto.check_hostname = False
            self._contexto.verify_mode = ssl.CERT_NONE

    def run(self) -> None:
        while not self._stop:
            try:
                with urllib.request.urlopen(self.url + "/estado",
                                            timeout=1.0,
                                            context=self._contexto) as r:
                    datos = json.loads(r.read().decode("utf-8"))
                if datos.get("fresh"):
                    self._estado = datos
                    self._ts = time.time()
            except Exception:
                pass  # el servidor aún no está o se cayó: se reintenta
            time.sleep(0.25)

    def detener(self) -> None:
        self._stop = True

    def orientacion(self) -> tuple | None:
        """(rumbo, inclinacion, roll) o None si no hay lectura fresca reciente."""
        if self._estado is None or time.time() - self._ts > 3.0:
            return None
        return (float(self._estado["rumbo"]),
                float(self._estado["inclinacion"]),
                float(self._estado.get("roll", 0.0)))


def _ubicacion(args, aviso=False) -> Ubicacion:
    ubicacion = cargar_ubicacion()
    if args.lat is not None and args.lon is not None:
        return Ubicacion(lat=args.lat, lon=args.lon, nombre="demo")
    if ubicacion is not None:
        return ubicacion
    if aviso:
        print("Aviso: sin data/ubicacion.json; se usa lat 10, lon -68.")
    return Ubicacion(lat=10.0, lon=-68.0, nombre="por defecto")


def run() -> int:
    parser = argparse.ArgumentParser(
        description="Demo de composición: cielo dentro del marco de las manos (F8)")
    parser.add_argument("--fov", type=float, default=60.0,
                        help="campo de visión horizontal en grados (def. 60)")
    parser.add_argument("--rumbo", type=float, default=180.0,
                        help="azimut inicial (def. 180 = sur)")
    parser.add_argument("--inclinacion", type=float, default=45.0,
                        help="altitud inicial en grados (def. 45)")
    parser.add_argument("--brillo", type=float, default=2.5,
                        help="factor de brillo de las estrellas (def. 2.5)")
    parser.add_argument("--borde-suave", type=float, default=2.0,
                        help="píxeles de fundido en el borde del marco (def. 2)")
    parser.add_argument("--etiquetas", dest="etiquetas_modo",
                        action="store_const", const="si", default="auto",
                        help="forzar los nombres de los astros siempre")
    parser.add_argument("--no-etiquetas", dest="etiquetas_modo",
                        action="store_const", const="no",
                        help="ocultar los nombres siempre")
    parser.add_argument("--etiquetas-auto", dest="etiquetas_modo",
                        action="store_const", const="auto",
                        help="nombres según el gesto: L sin nombres, "
                             "MANO_COMPLETA con nombres (def.)")
    parser.add_argument("--medidor", dest="medidor", action="store_true",
                        default=True,
                        help="mostrar el medidor de coordenadas del punto "
                             "bajo el cursor (def. sí)")
    parser.add_argument("--no-medidor", dest="medidor", action="store_false",
                        help="ocultar el medidor")
    parser.add_argument("--estetica", default="noche_profunda",
                        choices=sorted(ESTETICAS),
                        help="estética del cielo (def. noche_profunda)")
    parser.add_argument("--modo", default="ventana",
                        choices=Compositor.MODOS,
                        help="cómo incrustar el cielo en el marco: "
                             "'ventana' recorta el pedazo de cielo bajo el "
                             "marco (def.); 'completo' warpea todo el FOV")
    parser.add_argument("--brujula", default="",
                        help="URL del servidor de la brújula, p. ej. "
                             "https://localhost:8080 (debe ser https://; si se "
                             "omite, solo teclado)")
    parser.add_argument("--lat", type=float, help="latitud (si no, la guardada)")
    parser.add_argument("--lon", type=float, help="longitud (si no, la guardada)")
    parser.add_argument("--camera", type=int, default=0,
                        help="índice de la cámara web (def. 0)")
    args = parser.parse_args()

    ubicacion = _ubicacion(args, aviso=True)
    print(f"Ubicación: {ubicacion.nombre} (lat {ubicacion.lat:.4f}, "
          f"lon {ubicacion.lon:.4f})")

    brujula = CompassReader(args.brujula) if args.brujula else None
    if brujula:
        if args.brujula.startswith("http://"):
            print("Aviso: el servidor es solo TLS. La URL debe empezar por "
                  "https:// (con http:// la conexión se rechaza y la brújula "
                  "no recibe datos).")
        brujula.start()
        print(f"Brújula: leyendo de {args.brujula}/estado. "
              "Las flechas se ignoran mientras haya datos frescos.")

    rumbo, inclinacion = args.rumbo, args.inclinacion
    base = (rumbo, inclinacion)
    roll = 0.0
    etiquetas = False   # valor efectivo; en "auto" lo decide el gesto (F9)
    brillo = args.brillo

    renderer = SkyRenderer(ancho=1280, alto=720, fov_deg=args.fov,
                           brillo_factor=brillo, estetica=args.estetica)
    renderer.ubicacion = ubicacion
    compositor = Compositor(ancho=1280, alto=720,
                            borde_suave=args.borde_suave, modo=args.modo)
    ts = load.timescale()
    tick = fps_counter()

    print("Fase 8/9 — Composición. Flechas: rumbo/inclinación. "
          "[ / ]: brillo. n: etiquetas (auto/sí/no). e: estética. "
          "m: modo del marco. c: medidor del cursor. r: reiniciar. "
          "q/ESC: salir.")

    with CameraCapture(index=args.camera).open() as cam:
        pipeline = HandPipeline()
        cv2.namedWindow(WINDOW_NAME)
        cursor = {"x": -1, "y": -1}

        def on_mouse(event, x, y, flags, param):
            if event == cv2.EVENT_MOUSEMOVE:
                cursor["x"], cursor["y"] = x, y

        cv2.setMouseCallback(WINDOW_NAME, on_mouse)
        try:
            while True:
                frame = cam.read()
                if frame is None:
                    print("Aviso: la cámara dejó de entregar frames.")
                    break

                hand_frame = pipeline.process(frame)

                # --- orientación: brújula si está fresca, si no teclado ---
                if brujula is not None:
                    o = brujula.orientacion()
                    if o is not None:
                        rumbo, inclinacion, roll = o
                    else:
                        roll = 0.0

                # --- Fase 9: las etiquetas siguen al gesto (L sin nombres,
                # MANO_COMPLETA con nombres); con "si"/"no" se fuerzan ---
                if args.etiquetas_modo == "auto":
                    etiquetas = etiquetas_segun_gesto(hand_frame.mode, etiquetas)
                elif args.etiquetas_modo == "si":
                    etiquetas = True
                else:
                    etiquetas = False

                # --- cielo de esa dirección y composición ---
                cielo = renderer.render(ts.now(), rumbo % 360.0,
                                        inclinacion, roll,
                                        etiquetas=etiquetas)
                if hand_frame.valid:
                    salida = compositor.compone(frame, cielo,
                                                hand_frame.quad_smooth)
                else:
                    salida = frame

                # --- OSD ---
                fps = tick(time.perf_counter())
                cv2.putText(salida, f"FPS: {fps:5.1f}  rumbo {rumbo:6.1f}  "
                                    f"incl {inclinacion:5.1f}",
                            (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                            (0, 255, 0), 1, cv2.LINE_AA)
                if args.etiquetas_modo == "auto":
                    etq_label = f"auto ({'sí' if etiquetas else 'no'})"
                else:
                    etq_label = "sí" if etiquetas else "no"
                modo = (f"MODO: {hand_frame.mode}   etiquetas: {etq_label}   "
                        f"estética: {renderer.estetica}   "
                        f"marco: {compositor.modo}")
                if not hand_frame.valid:
                    modo += "   [SIN MARCO: forma una ventana con ambas manos]"
                cv2.putText(salida, modo, (10, 54),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                            (0, 255, 0) if hand_frame.valid else (0, 0, 255),
                            1, cv2.LINE_AA)

                # --- medidor: rumbo/alt exactos del punto bajo el cursor ---
                if args.medidor and cursor["x"] >= 0:
                    az, alt = renderer.altaz_del_pixel(
                        cursor["x"], cursor["y"], rumbo % 360.0,
                        inclinacion, roll)
                    _dibujar_medidor(salida, cursor["x"], cursor["y"], az, alt)

                cv2.imshow(WINDOW_NAME, salida)

                tecla = cv2.waitKey(1) & 0xFF
                if tecla in (ord("q"), 27):
                    break
                elif tecla in (81, ord("a")):          # flecha izquierda
                    rumbo -= 5.0
                elif tecla in (83, ord("d")):          # flecha derecha
                    rumbo += 5.0
                elif tecla in (82, ord("w")):          # flecha arriba
                    inclinacion = min(90.0, inclinacion + 5.0)
                elif tecla in (84, ord("s")):          # flecha abajo
                    inclinacion = max(-90.0, inclinacion - 5.0)
                elif tecla == ord("["):
                    brillo = max(0.1, round(brillo - 0.1, 2))
                    renderer.brillo_factor = brillo
                elif tecla == ord("]"):
                    brillo = min(3.0, round(brillo + 0.1, 2))
                    renderer.brillo_factor = brillo
                elif tecla == ord("n"):
                    ciclo = ("auto", "si", "no")
                    i = (ciclo.index(args.etiquetas_modo) + 1) % len(ciclo)
                    args.etiquetas_modo = ciclo[i]
                    desc = {"auto": "según el gesto (L sin nombres, "
                                    "MANO_COMPLETA con nombres)",
                            "si": "forzadas siempre sí",
                            "no": "forzadas siempre no"}[args.etiquetas_modo]
                    print(f"Etiquetas: {desc}")
                elif tecla == ord("e"):
                    nombres = sorted(ESTETICAS)
                    i = (nombres.index(renderer.estetica) + 1) % len(nombres)
                    renderer.estetica = nombres[i]
                    print(f"Estética del cielo: {renderer.estetica}")
                elif tecla == ord("c"):
                    args.medidor = not args.medidor
                    print("Medidor de coordenadas: "
                          f"{'mostrando' if args.medidor else 'oculto'}")
                elif tecla == ord("m"):
                    nombres = list(Compositor.MODOS)
                    i = (nombres.index(compositor.modo) + 1) % len(nombres)
                    compositor.modo = nombres[i]
                    print(f"Modo del marco: {compositor.modo}")
                elif tecla == ord("r"):
                    rumbo, inclinacion = base
        finally:
            pipeline.close()
            cv2.destroyAllWindows()
            if brujula is not None:
                brujula.detener()
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
