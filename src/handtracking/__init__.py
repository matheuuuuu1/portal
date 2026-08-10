"""Módulo handtracking: detección de manos y construcción del marco.

MediaPipe Hands extrae los landmarks 4 (pulgar), 8 (índice) y 12 (medio)
por mano, junto con la lateralidad, para construir el cuadrilátero de 4
esquinas del marco y seleccionar el modo de gesto (ADR-003 y ADR-004).
"""
