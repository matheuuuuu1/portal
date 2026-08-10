"""Módulo skyrender: astrometría y render del cielo.

Carga el catálogo de estrellas como vectores unitarios ecuatoriales, calcula
con skyfield la matriz de rotación ecuatorial→horizontal del instante y
proyecta con numpy vectorizado según la orientación de la cámara (ADR-005).
"""

from .astro import (RUTA_EFEMERIDES, RUTA_UBICACION, Ubicacion,
                    altaz_con_skyfield, altaz_desde_horizontal, aplicar_matriz,
                    cargar_ubicacion, guardar_ubicacion, lst_grados,
                    matriz_horizontal, matriz_vista_camara, precesionar_j2000,
                    precesionar_vectores_j2000)
from .catalogo import RUTA_CATALOGO, Catalogo, Estrella, cargar_estrellas
from .constelaciones import CONSTELACIONES, Constelacion, segmentos
from .render import NOMBRES_PROPIOS, SkyRenderer

__all__ = [
    "RUTA_CATALOGO", "RUTA_EFEMERIDES", "RUTA_UBICACION",
    "Ubicacion", "Estrella", "Catalogo",
    "cargar_estrellas", "cargar_ubicacion", "guardar_ubicacion",
    "precesionar_j2000", "precesionar_vectores_j2000",
    "lst_grados", "matriz_horizontal", "matriz_vista_camara",
    "aplicar_matriz", "altaz_desde_horizontal", "altaz_con_skyfield",
    "Constelacion", "CONSTELACIONES", "segmentos",
    "NOMBRES_PROPIOS", "SkyRenderer",
]
