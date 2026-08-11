"""Genera capturas comparativas de estilos estéticos para el cielo (preview).

Uso (desde la raíz del proyecto, venv activado):

    PYTHONPATH=src .venv/Scripts/python tools/previews_estetica.py

Renderiza el MISMO cielo (misma fecha/hora/orientación) con 4 estéticas y las
guarda en docs/previews/:

    00_actual.png         el render actual (referencia científica)
    01_noche_profunda.png degradado + halos en estrellas brillantes
    02_via_lactea.png     base + Vía Láctea (sintética) + fondo denso
    03_cinematico.png     tono azul noche + halos suaves + viñeta

Nota: "noche_profunda" es ahora la estética por defecto del render
(`SkyRenderer(estetica="noche_profunda")`), integrada en `skyrender/estetica.py`.
La captura 00 se genera con `estetica="plano"` para que sirva de referencia
científica sin post-proceso.

Es un script de diseño (no se usa en ejecución); sirve para decidir la
estética definitiva del render.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np
from skyfield.api import load

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from skyrender.astro import cargar_ubicacion  # noqa: E402
from skyrender.estetica import noche_profunda  # noqa: E402
from skyrender.render import SkyRenderer  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
SALIDA = RAIZ / "docs" / "previews"
ANCHO, ALTO = 1280, 720


def render_base(t, rumbo=180.0, inclinacion=45.0) -> np.ndarray:
    """Cielo científico sin post-proceso (estética 'plano') como referencia."""
    renderer = SkyRenderer(ancho=ANCHO, alto=ALTO, fov_deg=60.0,
                           brillo_factor=2.5, estetica="plano")
    ubicacion = cargar_ubicacion()
    renderer.ubicacion = ubicacion or renderer.ubicacion
    return renderer.render(t, rumbo % 360.0, inclinacion, etiquetas=True)


def _degradado(arriba, abajo) -> np.ndarray:
    """Degradado vertical de 'arriba' (fila0) a 'abajo' (fila H-1), BGR."""
    t = np.linspace(0.0, 1.0, ALTO, dtype=np.float32)[:, None, None]
    a = np.array(arriba, dtype=np.float32)[None, None, :]
    b = np.array(abajo, dtype=np.float32)[None, None, :]
    return (a * (1 - t) + b * t).astype(np.float32)


def _halo(img, umbral=50.0, sigma=8.0, factor=1.1) -> np.ndarray:
    """Máscara de resplandor a partir de las estrellas ya dibujadas."""
    gris = img[:, :, 1].astype(np.float32)  # canal verde ~ luminancia
    masc = np.clip((gris - umbral) / umbral, 0.0, 1.0)
    halo = cv2.GaussianBlur(masc, (0, 0), sigmaX=sigma, sigmaY=sigma)
    return np.clip(halo * factor, 0.0, 1.0)


def est_noche_profunda(img) -> np.ndarray:
    """La estética integrada por defecto (skyrender.estetica.noche_profunda)."""
    return noche_profunda(img)


def est_via_lactea(img) -> np.ndarray:
    """Base de noche profunda + banda de Vía Láctea sintética + fondo denso."""
    out = est_noche_profunda(img)
    rng = np.random.default_rng(2026)

    # Banda diagonal de la Vía Láctea (sintética, para decidir estética).
    yy = np.linspace(0, ALTO - 1, ALTO)[:, None]
    xx = np.linspace(0, ANCHO - 1, ANCHO)[None, :]
    banda = 0.5 + 0.5 * np.sin((xx + yy) * 0.011 + 2.0)
    banda = np.clip(banda, 0.0, 1.0)
    ruido = rng.random((ALTO, ANCHO))
    ml = banda * ruido
    ml = cv2.GaussianBlur(ml, (0, 0), sigmaX=20.0, sigmaY=20.0)
    ml = np.clip(ml * 2.4, 0.0, 1.0)
    out = out.astype(np.float32)
    out += ml[..., None] * np.array([120, 95, 155], dtype=np.float32) * 0.30

    # Estrellas de fondo sintéticas (débiles) para densificar el cielo.
    n = 1400
    xs = rng.integers(0, ANCHO, n)
    ys = rng.integers(0, ALTO, n)
    brillos = rng.uniform(8, 28, n)
    for xi, yi, bi in zip(xs, ys, brillos):
        out[yi, xi] = np.maximum(out[yi, xi], bi)
    return np.clip(out, 0, 255).astype(np.uint8)


def est_cinematico(img) -> np.ndarray:
    """Tono azul noche + halos amplios y suaves + viñeta cinematográfica."""
    fondo = _degradado((95, 48, 28), (20, 18, 32))
    out = fondo + img.astype(np.float32)
    # Halo amplio y suave (más cinematográfico).
    halo = _halo(img, umbral=40.0, sigma=13.0, factor=1.5)
    out += halo[..., None] * np.array([235, 228, 250], dtype=np.float32) * 0.45
    # Viñeta: oscurece bordes.
    yy = np.linspace(-1, 1, ALTO)[:, None]
    xx = np.linspace(-1, 1, ANCHO)[None, :]
    dist = np.sqrt(xx ** 2 + yy ** 2)
    vin = 1.0 - 0.35 * np.clip(dist, 0.0, 1.0) ** 2
    out *= vin[..., None]
    # Airglow suave en el horizonte (borde inferior).
    airglow = np.clip(np.linspace(0.0, 0.5, ALTO)[:, None, None]
                      * np.array([30, 60, 40], dtype=np.float32), 0, 255)
    out += airglow
    return np.clip(out, 0, 255).astype(np.uint8)


def main() -> int:
    ts = load.timescale()
    t = ts.from_datetime(datetime(2026, 8, 10, 2, 0, 0, tzinfo=timezone.utc))
    print("Generando capturas (rumbo 180 = sur, inclinación 45)...")

    SALIDA.mkdir(parents=True, exist_ok=True)
    base = render_base(t)
    estilos = [
        ("00_actual.png", base),
        ("01_noche_profunda.png", est_noche_profunda(base)),
        ("02_via_lactea.png", est_via_lactea(base)),
        ("03_cinematico.png", est_cinematico(base)),
    ]
    for nombre, img in estilos:
        ruta = SALIDA / nombre
        cv2.imwrite(str(ruta), img)
        print(f"  {ruta}  ({img.shape[1]}x{img.shape[0]})")
    print("Listo. Abre las 4 capturas para comparar.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
