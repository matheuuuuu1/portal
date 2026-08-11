"""Tests del render del cielo (Fase 7).

Requieren el catálogo BSC (`data/catalogo/bsc5.dat`) y las efemérides
(`data/models/de421.bsp`); se descargan con `tools/download_models.py`.
"""

from __future__ import annotations

import time
import unittest
from datetime import datetime, timezone

import numpy as np
from skyfield.api import load

from src.skyrender.astro import (RUTA_EFEMERIDES, aplicar_matriz,
                                 altaz_desde_horizontal, lst_grados,
                                 matriz_horizontal, matriz_vista_camara)
from src.skyrender.catalogo import RUTA_CATALOGO, cargar_estrellas
from src.skyrender.constelaciones import segmentos
from src.skyrender.render import NOMBRES_PROPIOS, SkyRenderer

_FECHA = datetime(2026, 8, 10, 12, 0, 0, tzinfo=timezone.utc)


def _t():
    return load.timescale().from_datetime(_FECHA)


@unittest.skipUnless(RUTA_CATALOGO.exists(), "Falta el catálogo BSC")
class TestConstelaciones(unittest.TestCase):
    def test_hay_segmentos_suficientes(self):
        c = cargar_estrellas(RUTA_CATALOGO)
        lineas = segmentos(c)
        self.assertGreaterEqual(len(lineas), 40)

    def test_extremos_resueltos_sin_duplicados(self):
        c = cargar_estrellas(RUTA_CATALOGO)
        lineas = segmentos(c)
        pares = set()
        for ea, eb in lineas:
            self.assertIsNotNone(ea)
            self.assertIsNotNone(eb)
            self.assertNotEqual(ea.id, eb.id)
            pares.add((min(ea.id, eb.id), max(ea.id, eb.id)))
        self.assertEqual(len(pares), len(lineas))


@unittest.skipUnless(RUTA_CATALOGO.exists(), "Falta el catálogo BSC")
class TestRender(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.renderer = SkyRenderer(ancho=1280, alto=720, fov_deg=60.0)

    def test_render_720p_con_estrellas(self):
        img = self.renderer.render(_t(), rumbo=180.0, inclinacion=45.0)
        self.assertEqual(img.shape, (720, 1280, 3))
        self.assertGreater(np.count_nonzero(img), 100,
                           "el cielo debe tener estrellas visibles")

    def test_render_apuntando_al_suelo_es_negro(self):
        # inclinacion -90 mira hacia el nadir; sin estética no hay estrellas
        # ni fondo, así que la imagen queda completamente negra.
        renderer = SkyRenderer(ancho=1280, alto=720, fov_deg=60.0,
                               estetica="plano")
        img = renderer.render(_t(), rumbo=180.0, inclinacion=-90.0)
        self.assertEqual(np.count_nonzero(img), 0)

    def test_proyeccion_centro(self):
        # Un vector apuntando exactamente al frente cae en el centro.
        u, v = self.renderer._proyectar(np.array([[0.0, 0.0, 1.0]]))
        self.assertAlmostEqual(u[0], self.renderer._cx, places=6)
        self.assertAlmostEqual(v[0], self.renderer._cy, places=6)
        # Un vector a la derecha se desplaza +fx en u.
        u2, v2 = self.renderer._proyectar(np.array([[1.0, 0.0, 1.0]]))
        self.assertAlmostEqual(u2[0], self.renderer._cx + self.renderer._fx,
                               places=6)
        self.assertAlmostEqual(v2[0], self.renderer._cy, places=6)

    def test_altaz_del_centro_es_la_orientacion_de_la_camara(self):
        # El píxel central ve exactamente el rumbo/inclinación de la cámara.
        for rumbo, incl in ((0.0, 45.0), (180.0, 0.0), (95.0, 30.0),
                            (350.0, 15.0)):
            az, alt = self.renderer.altaz_del_pixel(
                self.renderer._cx, self.renderer._cy, rumbo, incl)
            self.assertAlmostEqual(az % 360.0, rumbo % 360.0, places=6)
            self.assertAlmostEqual(alt, incl, places=6)

    def test_altaz_del_pixel_es_inversa_de_la_proyeccion(self):
        # Ida y vuelta: cada estrella dibujada se proyecta a un píxel y
        # `altaz_del_pixel` debe devolver su (rumbo, altitud) reales.
        r = self.renderer
        t = _t()
        rumbo, incl, roll = 180.0, 45.0, 0.0
        M_hor = matriz_horizontal(r.ubicacion.lat,
                                  lst_grados(r.ubicacion.lon, float(t.gast)))
        v_hor = aplicar_matriz(M_hor, r._v_ecuatoriales_aparentes(t))
        M_cam = matriz_vista_camara(rumbo, incl, roll)
        v_cam = aplicar_matriz(M_cam, v_hor)
        u, v = r._proyectar(v_cam)
        alt_real, az_real = altaz_desde_horizontal(v_hor)
        dibujadas = (v_hor[:, 2] > 0.0) & (v_cam[:, 2] > 0.0)
        visibles = np.where(dibujadas)[0]
        indices = visibles[:: max(1, len(visibles) // 40)]  # muestrea ~40
        self.assertGreater(len(indices), 0)
        for i in indices:
            az, alt = r.altaz_del_pixel(float(u[i]), float(v[i]),
                                        rumbo, incl, roll)
            self.assertAlmostEqual(alt, float(alt_real[i]), places=4)
            d = abs((az - float(az_real[i])) % 360.0)
            self.assertLess(min(d, 360.0 - d), 1e-3)

    def test_rendimiento_objetivo(self):
        t = _t()
        renderer = self.renderer
        renderer.render(t, 180.0, 45.0)  # calienta cachés
        inicio = time.perf_counter()
        for _ in range(10):
            renderer.render(t, 180.0, 45.0)
        total = time.perf_counter() - inicio
        promedio_ms = total / 10.0 * 1000.0
        self.assertLess(promedio_ms, 150.0,
                        f"el render es demasiado lento: {promedio_ms:.1f} ms")

    def test_nombres_propios_tiene_sirio(self):
        self.assertEqual(NOMBRES_PROPIOS.get("Alp CMa"), "Sirio")

    def test_etiquetas_resuelven_nombres_bsc(self):
        # El BSC guarda "9Alp CMa"; el render debe resolverlo a "Sirio" (HR 2491)
        # y "58Alp Ori" a "Betelgeuse" (HR 2061), no quedarse sin etiqueta.
        renderer = SkyRenderer(ancho=1280, alto=720, fov_deg=60.0)
        nombres = renderer._nombres_por_indice
        self.assertEqual(nombres.get(2491), "Sirio")
        self.assertEqual(nombres.get(2061), "Betelgeuse")
        self.assertEqual(nombres.get(7001), "Vega")

    def test_brillo_factor_aumenta_estrellas(self):
        base = SkyRenderer(ancho=1280, alto=720, fov_deg=60.0, brillo_factor=1.0)
        brillante = SkyRenderer(ancho=1280, alto=720, fov_deg=60.0,
                                brillo_factor=2.0)
        t = _t()
        img_base = base.render(t, 180.0, 45.0)
        img_alta = brillante.render(t, 180.0, 45.0)
        # Con el doble de brillo la imagen acumula más luz.
        self.assertGreater(int(img_alta.sum()), int(img_base.sum()))

    def test_brillo_factor_cambiable_en_caliente(self):
        renderer = SkyRenderer(ancho=1280, alto=720, fov_deg=60.0)
        t = _t()
        renderer.brillo_factor = 0.1
        img_bajo = renderer.render(t, 180.0, 45.0)
        renderer.brillo_factor = 2.5
        img_alto = renderer.render(t, 180.0, 45.0)
        self.assertGreater(int(img_alto.sum()), int(img_bajo.sum()))

    def test_estetica_por_defecto_es_noche_profunda(self):
        renderer = SkyRenderer(ancho=1280, alto=720, fov_deg=60.0)
        self.assertEqual(renderer.estetica, "noche_profunda")

    def test_estetica_por_defecto_pinta_fondo_degradado(self):
        # Mirando al suelo no hay estrellas, pero la estética por defecto
        # pinta igualmente el degradado azul noche como fondo.
        renderer = SkyRenderer(ancho=1280, alto=720, fov_deg=60.0)
        img = renderer.render(_t(), rumbo=180.0, inclinacion=-90.0)
        self.assertGreater(np.count_nonzero(img), 0,
                           "el degradado de fondo debe verse")
        # El degradado va de un azul más claro (arriba) a uno más oscuro
        # (abajo), como en el cielo nocturno real.
        self.assertGreater(float(img[0].mean()), float(img[-1].mean()))

    def test_estetica_noche_profunda_resalta_el_cielo(self):
        plano_r = SkyRenderer(ancho=1280, alto=720, fov_deg=60.0,
                              estetica="plano")
        profundo_r = SkyRenderer(ancho=1280, alto=720, fov_deg=60.0)
        t = _t()
        img_plano = plano_r.render(t, 180.0, 45.0)
        img_profundo = profundo_r.render(t, 180.0, 45.0)
        # Fondo + resplandor de las estrellas añaden luz visible.
        self.assertGreater(int(img_profundo.sum()), int(img_plano.sum()))

    def test_estetica_invalida_lanza(self):
        with self.assertRaises(ValueError):
            SkyRenderer(ancho=1280, alto=720, fov_deg=60.0,
                        estetica="no-existe")

    def test_estetica_cambiable_en_caliente(self):
        renderer = SkyRenderer(ancho=1280, alto=720, fov_deg=60.0)
        t = _t()
        img_profundo = renderer.render(t, 180.0, 45.0)
        renderer.estetica = "plano"
        img_plano = renderer.render(t, 180.0, 45.0)
        self.assertEqual(int(img_profundo.sum()) >= int(img_plano.sum()), True)


@unittest.skipUnless(RUTA_EFEMERIDES.exists(),
                     "Faltan las efemérides de421.bsp")
class TestPlanetas(unittest.TestCase):
    def test_planetas_horizontales_norma_unidad(self):
        renderer = SkyRenderer(ancho=1280, alto=720, fov_deg=60.0)
        planetas = renderer._planetas_horizontales(_t())
        self.assertGreaterEqual(len(planetas), 7)
        for nombre, v in planetas.items():
            with self.subTest(nombre=nombre):
                self.assertAlmostEqual(np.linalg.norm(v), 1.0, places=9)

    def test_render_con_planetas_no_lanza(self):
        renderer = SkyRenderer(ancho=1280, alto=720, fov_deg=60.0)
        img = renderer.render(_t(), rumbo=180.0, inclinacion=45.0)
        self.assertEqual(img.shape, (720, 1280, 3))


if __name__ == "__main__":
    unittest.main()
