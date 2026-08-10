"""Módulo skyrender: astrometría y render del cielo.

Carga el catálogo de estrellas como vectores unitarios ecuatoriales, calcula
con skyfield la matriz de rotación ecuatorial→horizontal del instante y
proyecta con numpy vectorizado según la orientación de la cámara (ADR-005).
"""
