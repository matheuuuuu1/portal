"""Módulo compositor: mezcla del feed de cámara con el cielo.

Calcula la homografía desde las 4 esquinas del marco y aplica
warpPerspective para incrustar el cielo renderizado dentro del cuadrilátero;
el resto del frame permanece igual.
"""
