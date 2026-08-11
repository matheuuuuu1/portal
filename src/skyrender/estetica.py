"""Estéticas de post-proceso para el cielo (decisión de diseño, no astronomía).

El render de `skyrender.render` calcula el cielo con precisión (precesión,
posición exacta de estrellas y planetas, constelaciones) y lo pinta sobre
fondo negro. Estas funciones aplican una capa estética encima —fondo con
degradado, resplandor en las estrellas brillantes— sin tocar la posición
de los astros: cada estrella sigue en su sitio exacto.

La estética por defecto es **noche_profunda** (elegida por Matheus el
2026-08-11 a partir de las capturas de `tools/previews_estetica.py`).
Se puede cambiar en la construcción de `SkyRenderer(estetica=...)` o en
caliente asignando `renderer.estetica`.
"""

from __future__ import annotations

from typing import Callable, Optional

import cv2
import numpy as np

# --- Paleta de "Noche profunda" (todo en BGR) ---
_ARRIBA = (85, 42, 30)          # azul noche, arriba
_ABAJO = (22, 16, 26)           # azul-negro profundo, abajo
_HALO_COLOR = (255, 248, 240)   # blanco-azulado: luz de las estrellas
_HALO_UMBRAL = 60.0
_HALO_SIGMA = 7.0
_HALO_FACTOR = 1.15
_HALO_INTENSIDAD = 0.55


def degradado_vertical(ancho: int, alto: int,
                       arriba: tuple[int, int, int],
                       abajo: tuple[int, int, int]) -> np.ndarray:
    """Degradado vertical BGR (alto, ancho, 3): fila 0 = 'arriba'."""
    t = np.linspace(0.0, 1.0, alto, dtype=np.float32)[:, None, None]
    a = np.array(arriba, dtype=np.float32)[None, None, :]
    b = np.array(abajo, dtype=np.float32)[None, None, :]
    grad = (a * (1 - t) + b * t).astype(np.float32)      # (alto, 1, 3)
    return np.broadcast_to(grad, (alto, ancho, 3)).copy()


def fondo_noche_profunda(ancho: int, alto: int) -> np.ndarray:
    """Degradado de fondo por defecto de la estética 'noche_profunda'."""
    return degradado_vertical(ancho, alto, _ARRIBA, _ABAJO)


def _halo_resplandor(img: np.ndarray, umbral: float, sigma: float,
                     factor: float, desescala: int = 4) -> np.ndarray:
    """Máscara de resplandor a partir de las estrellas ya dibujadas.

    Se usa el canal verde de la imagen como aproximación de la luminancia:
    las estrellas brillantes quedan blancas (255) y las tenues oscuras.
    La máscara difuminada marca dónde añadir luz alrededor de cada astro.

    Para que el render siga en tiempo real, el resplandor se trabaja a 1/4
    de resolución (el halo es suave: a sigma grandes equivale a difuminar
    el original) y después se vuelve a escalar. El umbral se aplica sobre
    la imagen pequeña, así no hay operaciones de trama completa.
    """
    gris = img[:, :, 1]                     # uint8, canal verde ~ luminancia
    pequena = cv2.resize(gris, None, fx=1.0 / desescala, fy=1.0 / desescala,
                         interpolation=cv2.INTER_AREA).astype(np.float32)
    masc = np.clip((pequena - umbral) / umbral, 0.0, 1.0)
    halo = cv2.GaussianBlur(masc, (0, 0),
                            sigmaX=sigma / desescala,
                            sigmaY=sigma / desescala)
    halo = np.clip(halo * factor, 0.0, 1.0)
    if desescala > 1:
        halo = cv2.resize(halo, (img.shape[1], img.shape[0]),
                          interpolation=cv2.INTER_LINEAR)
    return halo


def noche_profunda(img: np.ndarray,
                   fondo: Optional[np.ndarray] = None) -> np.ndarray:
    """Degradado azul noche + resplandor blanco-azulado en las estrellas.

    'fondo' puede venir precalculado del renderer (se crea una sola vez
    para su tamaño de imagen); si no se pasa, se calcula aquí mismo.
    El fondo se redondea a uint8 para sumar con `cv2.add` (satura y es
    mucho más rápido que una suma float32 de trama completa).
    """
    if fondo is None:
        alto, ancho = img.shape[:2]
        fondo = fondo_noche_profunda(ancho, alto)
    if fondo.dtype != np.uint8:
        fondo = np.clip(fondo, 0, 255).astype(np.uint8)
    base = cv2.add(fondo, img)             # suma saturada uint8
    halo = _halo_resplandor(img, _HALO_UMBRAL, _HALO_SIGMA, _HALO_FACTOR)
    # El resplandor añade luz fraccionaria: se suma en float32 (una sola
    # copia) y se satura con convertScaleAbs, más rápido que clip+astype.
    color = np.array(_HALO_COLOR, dtype=np.float32) * _HALO_INTENSIDAD
    out = base.astype(np.float32)
    out[:, :, 0] += halo * color[0]
    out[:, :, 1] += halo * color[1]
    out[:, :, 2] += halo * color[2]
    return cv2.convertScaleAbs(out)


def plano(img: np.ndarray, fondo: Optional[np.ndarray] = None) -> np.ndarray:
    """Sin estética: el render científico sobre negro (comportamiento original)."""
    return img


# Registro de estéticas disponibles (nombre → función).
ESTETICAS: dict[str, Callable[[np.ndarray, Optional[np.ndarray]], np.ndarray]] = {
    "plano": plano,
    "noche_profunda": noche_profunda,
}


def aplicar(img: np.ndarray, nombre: str,
            fondo: Optional[np.ndarray] = None) -> np.ndarray:
    """Aplica la estética 'nombre' a la imagen (desconocida → plano)."""
    return ESTETICAS.get(nombre, plano)(img, fondo)
