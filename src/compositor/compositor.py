"""Composición: incrustar el cielo dentro del marco de las manos (Fase 8).

`Compositor` une las tres entradas del pipeline:

- el **frame de cámara** (BGR, 1280x720, de `app.capture.CameraCapture`),
- el **cuadrilátero del marco** (4 esquinas normalizadas TL, TR, BR, BL, de
  `handtracking.pipeline.HandPipeline`),
- la **imagen del cielo** (BGR, misma resolución que el frame, de
  `skyrender.render.SkyRenderer`).

Calcula la homografía desde las esquinas de la imagen del cielo hacia las 4
esquinas del cuadrilátero y aplica `cv2.warpPerspective`, de modo que la
porción de cielo que corresponde a la dirección de la cámara aparece dentro
del marco. El resto del frame permanece intacto.

La imagen del cielo se proyecta con la MISMA matriz de cámara y el mismo FOV
que el frame (el render llena toda la ventana); el marco simplemente recorta
el subconjunto que el usuario encierra con las manos, por lo que las estrellas
dentro del marco son las reales de esa dirección.
"""

from __future__ import annotations

from typing import Optional, Sequence, Tuple

import cv2
import numpy as np

from handtracking.quadrilateral import MIN_AREA, polygon_area

# Resolución objetivo del pipeline completo (ADR-007).
OBJ_WIDTH = 1280
OBJ_HEIGHT = 720


def quad_a_pixeles(quad: Sequence[Tuple[float, float]],
                   ancho: int, alto: int) -> list[tuple[float, float]]:
    """Convierte el cuadrilátero normalizado [0,1] a coordenadas de píxel."""
    return [(x * ancho, y * alto) for x, y in quad]


def homografia_marco(quad_px, ancho: int, alto: int) -> np.ndarray:
    """Homografía 3x3 que lleva las esquinas de la imagen del cielo al marco.

    La fuente son las 4 esquinas de la imagen del cielo (TL, TR, BR, BL) y el
    destino el cuadrilátero del marco en píxeles (mismo orden). Aplicar esta
    matriz con `cv2.warpPerspective` deja el cielo recortado por el marco.
    """
    src = np.array([(0, 0), (ancho - 1, 0), (ancho - 1, alto - 1),
                    (0, alto - 1)], dtype=np.float32)
    dst = np.array(quad_px, dtype=np.float32).reshape(-1, 2)
    return cv2.getPerspectiveTransform(src, dst)


def _mascara_u8(quad_px, ancho: int, alto: int,
                borde_suave: float = 0.0) -> np.ndarray:
    """Máscara uint8 0..255 con el interior del marco relleno.

    Con `borde_suave > 0` píxeles, el borde se difumina (gaussiano) para que el
    cielo funda con la cámara en lugar de recortarse con un borde duro. El
    blending del compositor trabaja en uint8 (multiplicación OpenCV), así que
    la máscara se conserva en este tipo para no pagar conversiones.
    """
    pts = np.array(quad_px, dtype=np.int32).reshape(-1, 1, 2)
    mascara = np.zeros((alto, ancho), dtype=np.uint8)
    cv2.fillConvexPoly(mascara, pts, 255)
    if borde_suave > 0.0:
        k = int(round(2.0 * borde_suave + 1.0))
        if k < 3:
            k = 3
        if k % 2 == 0:
            k += 1
        mascara = cv2.GaussianBlur(mascara, (k, k), 0)
    return mascara


def mascara_marco(quad_px, ancho: int, alto: int,
                  borde_suave: float = 0.0) -> np.ndarray:
    """Máscara de un canal en [0,1] con el interior del marco relleno.

    Forma float32 para usos de mezcla float; el compositor interno usa la
    versión uint8 (`_mascara_u8`) por rendimiento.
    """
    return _mascara_u8(quad_px, ancho, alto, borde_suave).astype(np.float32) / 255.0


def _mezclar(frame: np.ndarray, warpeado: np.ndarray,
             mascara_u8: np.ndarray) -> np.ndarray:
    """Blending alfa `salida = warpeado*m + frame*(1-m)` todo en uint8.

    Con `mascara_u8` en 0..255 y operaciones OpenCV vectorizadas (multiply y
    add), es una de las formas más rápidas de mezclar dos imágenes BGR. Con
    borde duro (m ∈ {0,255}) deja el resto del frame byte a byte intacto.
    """
    m3 = cv2.merge([mascara_u8, mascara_u8, mascara_u8])
    cielo = cv2.multiply(warpeado, m3, scale=1.0 / 255.0)
    resto = cv2.multiply(frame, cv2.subtract(255, m3), scale=1.0 / 255.0)
    return cv2.add(cielo, resto)


class Compositor:
    """Mezcla el feed de cámara con el cielo dentro del cuadrilátero del marco.

    Uso::

        compositor = Compositor(borde_suave=2.0)
        salida = compositor.compone(frame_bgr, cielo_bgr, quad_normalizado)

    `quad_normalizado` puede ser None (o degenerado): entonces se devuelve el
    frame tal cual, sin modificar.
    """

    def __init__(self, ancho: int = OBJ_WIDTH, alto: int = OBJ_HEIGHT,
                 borde_suave: float = 0.0,
                 min_area: float = MIN_AREA) -> None:
        self.ancho = ancho
        self.alto = alto
        self.borde_suave = borde_suave
        self.min_area = min_area

    def compone(self, frame_bgr: np.ndarray, cielo_bgr: np.ndarray,
                quad: Optional[Sequence[Tuple[float, float]]]) -> np.ndarray:
        """Devuelve el frame con el cielo incrustado dentro del marco.

        Sin marco (None), cuadrilátero inválido o resolución inesperada, se
        devuelve el frame original. Con marco, se warpea el cielo hacia el
        cuadrilátero y se mezcla; el resto de los píxeles no cambia.
        """
        # Validación de defensa: el pipeline ya valida, pero ante cualquier
        # degeneración (área mínima, esquinas colineales) se conserva el frame.
        if (quad is None or len(quad) != 4
                or polygon_area(quad) < self.min_area):
            return frame_bgr
        if frame_bgr.shape[:2] != (self.alto, self.ancho):
            return frame_bgr

        quad_px = quad_a_pixeles(quad, self.ancho, self.alto)
        try:
            M = homografia_marco(quad_px, self.ancho, self.alto)
            warpeado = cv2.warpPerspective(
                cielo_bgr, M, (self.ancho, self.alto),
                flags=cv2.INTER_LINEAR,
                borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        except cv2.error:
            return frame_bgr  # cuadrilátero no invertible -> marco intacto

        mascara = _mascara_u8(quad_px, self.ancho, self.alto, self.borde_suave)
        return _mezclar(frame_bgr, warpeado, mascara)
