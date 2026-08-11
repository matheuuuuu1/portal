"""Módulo compositor: mezcla del feed de cámara con el cielo (Fase 8).

Recibe el frame de cámara, el cuadrilátero del marco (4 esquinas normalizadas)
y la imagen del cielo renderizada. Calcula la homografía desde las esquinas de
la imagen del cielo hacia el cuadrilátero y aplica `cv2.warpPerspective` para
incrustar el cielo dentro del marco; el resto del frame permanece intacto.
"""

from .compositor import (Compositor, homografia_marco, mascara_marco,
                         quad_a_pixeles)

__all__ = ["Compositor", "homografia_marco", "mascara_marco", "quad_a_pixeles"]
