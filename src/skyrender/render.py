"""Render del cielo estrellado para la dirección de la cámara (Fase 7).

`SkyRenderer` lleva las estrellas del catálogo desde el marco ecuatorial
J2000 hasta píxeles de una imagen, todo vectorizado con numpy:

1. **Precesión** J2000 → marco aparente del instante (cacheada: la
   precesión-nutación apenas cambia en horas; se recalcula cada ~6 horas).
2. **Matriz ecuatorial → horizontal** del instante (LST + latitud).
3. **Matriz de vista de cámara** a partir de {rumbo, inclinacion, roll}.
4. **Proyección** perspectiva (FOV configurable) y dibujo de puntos según
   la magnitud, líneas de constelaciones, planetas (de421.bsp) y etiquetas.
5. **Estética** de post-proceso (degradado azul noche + resplandor en las
   estrellas brillantes), configurable con `estetica` (ver `estetica.py`).

El coste por frame es la proyección de los ~8.400 vectores (una
multiplicación de matrices) más el dibujo; los planetas se recalculan con
skyfield solo cuando el reloj avanza ~1 minuto.
"""

from __future__ import annotations

import math
import re
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from skyfield.api import load, wgs84

from .astro import (RUTA_EFEMERIDES, Ubicacion, aplicar_matriz,
                    altaz_desde_horizontal, cargar_ubicacion, lst_grados,
                    matriz_horizontal, matriz_vista_camara,
                    precesionar_vectores_j2000)
from .catalogo import RUTA_CATALOGO, Catalogo, cargar_estrellas
from .constelaciones import CONSTELACIONES, segmentos
from .estetica import ESTETICAS, aplicar, fondo_noche_profunda

# Nombres propios de las estrellas más brillantes. El campo Name del BSC
# solo lleva la designación Bayer/Flamsteed, así que el nombre común se
# asigna aquí para las etiquetas (la Fase 9 decidirá cuándo mostrarlas).
NOMBRES_PROPIOS: dict[str, str] = {
    "Alp CMa": "Sirio", "Alp Car": "Canopo", "Alp Boo": "Arturo",
    "Alp Cen": "Rigil Kentaurus", "Alp Lyr": "Vega", "Bet Ori": "Rigel",
    "Alp CMi": "Procyon", "Alp Eri": "Achernar", "Alp Ori": "Betelgeuse",
    "Bet Cen": "Hadar", "Alp Aql": "Altair", "Alp Sco": "Antares",
    "Alp Vir": "Espiga", "Alp PsA": "Fomalhaut", "Bet Gem": "Pólux",
    "Alp Cyg": "Deneb", "Alp And": "Alpheratz", "Alp UMi": "Polaris",
    "Alp Tau": "Aldebarán", "Alp Aur": "Capella", "Alp Gem": "Cástor",
    "Eps UMa": "Alioth", "Eta UMa": "Alkaid", "Alp UMa": "Dubhe",
    "Alp Cru": "Acrux", "Alp Leo": "Régulo", "Alp Gru": "Alnair",
    "Alp Sgr": "Rukbat", "Bet UMi": "Kochab", "Alp Cas": "Schedar",
}

# Planetas de de421.bsp (nombre de etiqueta, nombre del cuerpo en skyfield).
_PLANETAS: tuple[tuple[str, str], ...] = (
    ("Mercurio", "mercury"),
    ("Venus", "venus"),
    ("Marte", "mars"),
    ("Júpiter", "jupiter barycenter"),
    ("Saturno", "saturn barycenter"),
    ("Urano", "uranus barycenter"),
    ("Neptuno", "neptune barycenter"),
    ("Luna", "moon"),
)

# Magnitudes típicas de los planetas y la Luna, para ordenar la lista de
# objetos visibles por brillo. Son valores aproximados (no de una fecha
# concreta), solo de ordenación; no se muestran como dato.
_MAG_PLANETA: dict[str, float] = {
    "Luna": -12.7, "Venus": -4.5, "Júpiter": -2.5, "Saturno": 0.5,
    "Mercurio": 0.0, "Marte": 1.0, "Urano": 5.7, "Neptuno": 7.9,
}

_MAG_LIMITE = 6.5          # umbral del catálogo
_MAG_CIRCULO = 1.6         # estrellas que se dibujan como círculo
_COLOR_CONSTELACION = (130, 125, 90)    # azul apagado y sutil, BGR
_COLOR_PLANETA = (0, 200, 255)          # amarillo cálido, BGR
_COLOR_ETIQUETA = (255, 255, 255)


class SkyRenderer:
    def __init__(self,
                 catalogo: Optional[Catalogo] = None,
                 ubicacion: Optional[Ubicacion] = None,
                 ancho: int = 1280,
                 alto: int = 720,
                 fov_deg: float = 60.0,
                 brillo_factor: float = 2.5,
                 estetica: str = "noche_profunda",
                 ruta_catalogo: Path | str = RUTA_CATALOGO,
                 ruta_efemerides: Path | str = RUTA_EFEMERIDES) -> None:
        self.catalogo = catalogo or cargar_estrellas(ruta_catalogo)
        self.ubicacion = ubicacion or cargar_ubicacion() \
            or Ubicacion(lat=10.0, lon=-68.0, nombre="por defecto")
        self.ancho = ancho
        self.alto = alto
        self.fov_deg = fov_deg
        self.brillo_factor = brillo_factor
        if estetica not in ESTETICAS:
            raise ValueError(
                f"Estética desconocida: {estetica!r}. "
                f"Disponibles: {', '.join(sorted(ESTETICAS))}.")
        self.estetica = estetica
        self._fondo_est: Optional[np.ndarray] = None   # degradado, bajo demanda

        # Proyección perspectiva (píxeles cuadrados).
        f = (ancho / 2.0) / math.tan(math.radians(fov_deg) / 2.0)
        self._fx = f
        self._fy = f
        self._cx = (ancho - 1) / 2.0
        self._cy = (alto - 1) / 2.0

        # Vectores ecuatoriales J2000 (una sola vez; las estrellas no se
        # mueven perceptiblemente a escala humana).
        self._v_j2000 = self.catalogo.vectores_ecuatoriales()
        self._t_cache: object = None
        self._v_aparente: np.ndarray = np.zeros((0, 3))

        # Índices de las estrellas que forman los segmentos de constelaciones.
        id_a_indice = {e.id: i for i, e in enumerate(self.catalogo.estrellas)}
        self._segmentos_idx: list[tuple[int, int]] = [
            (id_a_indice[ea.id], id_a_indice[eb.id])
            for ea, eb in segmentos(self.catalogo)]
        # Estrellas miembro por constelación (para la lista de objetos; se
        # resuelven una sola vez al construir el renderer).
        self._constelaciones: list[tuple[str, list[int]]] = []
        for constelacion in CONSTELACIONES:
            miembros = [
                id_a_indice[e.id]
                for a, _b in constelacion.segmentos
                if (e := self.catalogo.buscar_designacion(a)) is not None
            ]
            self._constelaciones.append((constelacion.nombre, miembros))
        self._nombres_por_indice: dict[int, str] = {}
        for e in self.catalogo.estrellas:
            # El nombre del BSC es "9Alp CMa" (número Flamsteed + Bayer +
            # constelación) o "Alp1Cru" (componente: letra Bayer + dígito +
            # constelación, concatenados sin espacio). Se quitan los dígitos
            # y se separa la constelación de 3 letras para casar con las
            # claves de NOMBRES_PROPIOS ("Alp1Cru" -> "Alp Cru", "9Alp CMa"
            # -> "Alp CMa"). Sin esto, "Alp Cen"/"Alp Cru" (Rigil Kentaurus
            # y Acrux) nunca se asignan (bug 1.2).
            partes = e.nombre.split()
            if not partes:
                continue
            bayer = re.sub(r"\d", "", partes[0])   # "Alp1Cru" -> "AlpCru"
            resto = partes[1:]
            if len(bayer) > 3:
                # Componente del BSC: las últimas 3 letras son la
                # constelación ("AlpCru" -> "Alp" + "Cru").
                constelacion = bayer[-3:]
                bayer = bayer[:-3]
                resto = [constelacion] + resto
            clave = " ".join([bayer] + resto).strip()
            propio = NOMBRES_PROPIOS.get(clave, "")
            if propio:
                self._nombres_por_indice[e.id] = propio

        # Planetas (opcionales: requieren de421.bsp).
        self._ts = load.timescale()
        self._topos = None
        self._bodies: list[tuple[str, object]] = []
        ruta = Path(ruta_efemerides)
        if ruta.exists():
            eph = load(str(ruta))
            self._topos = eph["earth"] + wgs84.latlon(
                self.ubicacion.lat, self.ubicacion.lon)
            for nombre, clave in _PLANETAS:
                self._bodies.append((nombre, eph[clave]))
        self._planetas_cache: dict[str, tuple[float, float, float]] = {}
        self._planetas_t: object = None

    # ------------------------------------------------------------------
    # Astronomía por frame
    # ------------------------------------------------------------------

    def _v_ecuatoriales_aparentes(self, t) -> np.ndarray:
        """Vectores [N,3] en el marco aparente del instante (cacheado)."""
        if (self._t_cache is None
                or abs(float(t.tt) - float(self._t_cache.tt)) > 0.25):
            self._t_cache = t
            self._v_aparente = precesionar_vectores_j2000(self._v_j2000, t)
        return self._v_aparente

    def _planetas_horizontales(self, t) -> dict[str, tuple[float, float, float]]:
        """Planetas en vectores del marco local N-E-cénit (cacheado ~1 min)."""
        if self._topos is None:
            return {}
        if (self._planetas_t is None
                or abs(float(t.tt) - float(self._planetas_t.tt)) > 1.0 / 1440.0):
            self._planetas_t = t
            self._planetas_cache = {}
            for nombre, cuerpo in self._bodies:
                aparente = self._topos.at(t).observe(cuerpo).apparent()
                alt, az, _ = aparente.altaz()
                al, az_d = alt.degrees, az.degrees % 360.0
                self._planetas_cache[nombre] = (
                    math.cos(math.radians(al)) * math.cos(math.radians(az_d)),
                    math.cos(math.radians(al)) * math.sin(math.radians(az_d)),
                    math.sin(math.radians(al)),
                )
        return self._planetas_cache

    # ------------------------------------------------------------------
    # Proyección
    # ------------------------------------------------------------------

    def _proyectar(self, v_cam: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Vectores [N,3] en el marco de la cámara → (u, v) en píxeles."""
        z = v_cam[:, 2]
        u = self._cx + self._fx * v_cam[:, 0] / z
        v = self._cy - self._fy * v_cam[:, 1] / z
        return u, v

    def altaz_del_pixel(self, u: float, v: float, rumbo: float,
                        inclinacion: float, roll: float = 0.0
                        ) -> tuple[float, float]:
        """Dirección del cielo (rumbo, altitud) que cae en el píxel (u, v).

        Es la inversa de `_proyectar`: dado un píxel de la imagen, devuelve el
        (rumbo, altitud) del cielo que vería ahí la cámara apuntada con esa
        orientación. Útil para el medidor de la demo (qué punto del cielo está
        bajo el cursor) y para validar contra Stellarium.
        """
        # Rayo por el píxel en el marco de la cámara (z = adelante), normalizado.
        x_cam = (u - self._cx) / self._fx
        y_cam = (self._cy - v) / self._fy
        z_cam = 1.0
        norma = math.hypot(x_cam, math.hypot(y_cam, z_cam))
        v_cam = np.array([x_cam / norma, y_cam / norma, z_cam / norma],
                         dtype=np.float64)
        # Al marco horizontal con la transpuesta (la matriz de vista es
        # ortonormal: la inversa es su traspuesta).
        M = matriz_vista_camara(rumbo, inclinacion, roll)
        v_hor = M.T @ v_cam
        alt = math.degrees(math.asin(float(np.clip(v_hor[2], -1.0, 1.0))))
        az = math.degrees(math.atan2(v_hor[1], v_hor[0])) % 360.0
        return az, alt

    # ------------------------------------------------------------------
    # Consulta de objetos visibles (lista de la demo)
    # ------------------------------------------------------------------

    def objetos_visibles(self, t, rumbo: float, inclinacion: float,
                         roll: float = 0.0) -> list[dict]:
        """Objetos celestes a la vista en la orientación actual.

        Devuelve una lista de dicts ``{"tipo", "nombre", "az", "alt", "mag"}``
        con las estrellas con nombre propio, los planetas (y la Luna) y las
        constelaciones que caen dentro del encuadre de la cámara. ``az`` y
        ``alt`` son el punto al que apuntar para centrar el objeto; ``mag`` es
        la magnitud (``None`` para las constelaciones) y solo se usa para
        ordenar la lista por brillo: primero las estrellas y planetas más
        brillantes y al final las constelaciones por orden alfabético.

        Es la información que usa la demo para la lista de la tecla ``o``.
        """
        v_eq = self._v_ecuatoriales_aparentes(t)
        if len(v_eq) == 0:
            return []

        lat = self.ubicacion.lat
        lst = lst_grados(self.ubicacion.lon, float(t.gast))
        M_hor = matriz_horizontal(lat, lst)
        v_hor = aplicar_matriz(M_hor, v_eq)
        M_cam = matriz_vista_camara(rumbo, inclinacion, roll)
        v_cam = aplicar_matriz(M_cam, v_hor)

        z = v_cam[:, 2]
        frente = z > 0.0
        sobre_horizonte = v_hor[:, 2] > 0.0
        u, v = self._proyectar(v_cam)
        dentro = (frente & sobre_horizonte
                  & (u >= 0) & (u < self.ancho)
                  & (v >= 0) & (v < self.alto))
        idx_dentro = np.where(dentro)[0]

        objetos: list[dict] = []

        # --- estrellas con nombre propio dentro del encuadre ---
        if len(idx_dentro):
            alt, az = altaz_desde_horizontal(v_hor[idx_dentro])
            for i, (a, azi) in enumerate(zip(alt, az)):
                j = int(idx_dentro[i])
                nombre = self._nombres_por_indice.get(
                    int(self.catalogo.estrellas[j].id))
                if not nombre:
                    continue
                objetos.append({
                    "tipo": "estrella", "nombre": nombre,
                    "az": float(azi), "alt": float(a),
                    "mag": float(self.catalogo.estrellas[j].mag),
                })

        # --- planetas y la Luna dentro del encuadre ---
        for nombre, (px, py, pz) in self._planetas_horizontales(t).items():
            if pz <= 0.0:            # bajo el horizonte
                continue
            vc = M_cam @ np.array([px, py, pz])
            if vc[2] <= 0.0:
                continue
            uu = self._cx + self._fx * vc[0] / vc[2]
            vv = self._cy - self._fy * vc[1] / vc[2]
            if not (0 <= uu < self.ancho and 0 <= vv < self.alto):
                continue
            alt_p = math.degrees(math.asin(float(np.clip(pz, -1.0, 1.0))))
            az_p = math.degrees(math.atan2(py, px)) % 360.0
            objetos.append({
                "tipo": "planeta", "nombre": nombre,
                "az": az_p, "alt": alt_p,
                "mag": _MAG_PLANETA[nombre],
            })

        # --- constelaciones con al menos una estrella a la vista ---
        for nombre_c, miembros in self._constelaciones:
            idx_m = np.asarray(miembros, dtype=int)
            if len(idx_m) == 0 or not np.isin(idx_m, idx_dentro).any():
                continue
            # Centro: media de los vectores horizontales de los miembros
            # sobre el horizonte (aunque no estén en el encuadre).
            sobre_h = idx_m[v_hor[idx_m, 2] > 0.0]
            if len(sobre_h) == 0:
                continue
            centro = v_hor[sobre_h].mean(axis=0)
            norma = np.linalg.norm(centro)
            if norma < 1e-12:
                continue
            centro = centro / norma
            alt_c = math.degrees(math.asin(
                float(np.clip(centro[2], -1.0, 1.0))))
            az_c = math.degrees(math.atan2(centro[1], centro[0])) % 360.0
            objetos.append({
                "tipo": "constelacion", "nombre": nombre_c,
                "az": az_c, "alt": alt_c, "mag": None,
            })

        # Orden: astros por brillo (mag menor primero), luego constelaciones
        # por nombre.
        objetos.sort(key=lambda o: (
            o["mag"] is None,
            o["mag"] if o["mag"] is not None else 0.0,
            o["nombre"],
        ))
        return objetos

    def _fondo_estetica(self) -> np.ndarray:
        """Degradado de fondo de la estética en uint8, creado una sola vez."""
        if self._fondo_est is None:
            f = fondo_noche_profunda(self.ancho, self.alto)
            self._fondo_est = np.clip(f, 0, 255).astype(np.uint8)
        return self._fondo_est

    # ------------------------------------------------------------------
    # Dibujo
    # ------------------------------------------------------------------

    def render(self, t, rumbo: float, inclinacion: float, roll: float = 0.0,
               etiquetas: bool = True) -> np.ndarray:
        """Imagen BGR con el cielo según la orientación de la cámara."""
        img = np.zeros((self.alto, self.ancho, 3), dtype=np.uint8)

        v_eq = self._v_ecuatoriales_aparentes(t)
        if len(v_eq) == 0:
            return img

        lat = self.ubicacion.lat
        lst = lst_grados(self.ubicacion.lon, float(t.gast))
        M_hor = matriz_horizontal(lat, lst)
        v_hor = aplicar_matriz(M_hor, v_eq)
        M_cam = matriz_vista_camara(rumbo, inclinacion, roll)
        v_cam = aplicar_matriz(M_cam, v_hor)

        z = v_cam[:, 2]
        frente = z > 0.0
        # Solo la bóveda celeste visible: las estrellas bajo el horizonte
        # (alt < 0, z del marco horizontal < 0) quedan ocultas por la Tierra.
        sobre_horizonte = v_hor[:, 2] > 0.0
        u, v = self._proyectar(v_cam)
        dentro = (frente & sobre_horizonte
                  & (u >= 0) & (u < self.ancho)
                  & (v >= 0) & (v < self.alto))

        # --- puntos de todas las estrellas (vectorizado) ---
        mags = np.array([e.mag for e in self.catalogo.estrellas])
        # Compresión con raíz cuadrada: mags débiles suben de brillo sin
        # que las brillantes se saturen de más.  mag 6.5 ≈ 32, mag 2 ≈ 255.
        # brillo_factor escala el resultado (1.0 = referencia; >1 = más
        # brillantes, <1 = más tenues).  Se puede ajustar en caliente
        # cambiando `renderer.brillo_factor` entre frames.
        b = np.clip(255.0 * (10.0 ** (-0.4 * (mags - 2.0))) ** 0.5
                    * self.brillo_factor,
                    0.0, 255.0)
        idx = np.where(dentro)[0]
        if len(idx):
            ui = np.clip(u[idx].astype(int), 0, self.ancho - 1)
            vi = np.clip(v[idx].astype(int), 0, self.alto - 1)
            bval = b[idx].astype(np.uint8)
            # Puntos débiles: se asignan directamente (máximo local).
            img[vi, ui] = np.maximum(img[vi, ui], bval[:, None])

            # Las brillantes además se dibujan como círculos (halo).
            brillantes = idx[mags[idx] < _MAG_CIRCULO]
            for i in brillantes:
                radio = max(1, min(9, int(round(5.6 - mags[i] * 1.6))))
                cv2.circle(img, (int(u[i]), int(v[i])), radio,
                           (int(b[i]), int(b[i]), int(b[i])), -1)

        # --- líneas de constelaciones ---
        for i, j in self._segmentos_idx:
            if (z[i] > 0.0 and z[j] > 0.0
                    and v_hor[i, 2] > 0.0 and v_hor[j, 2] > 0.0):
                cv2.line(img,
                         (int(u[i]), int(v[i])),
                         (int(u[j]), int(v[j])),
                         _COLOR_CONSTELACION, 1)

        # --- planetas y la Luna ---
        for nombre, (px, py, pz) in self._planetas_horizontales(t).items():
            if pz <= 0.0:            # bajo el horizonte
                continue
            vc = M_cam @ np.array([px, py, pz])
            if vc[2] <= 0.0:
                continue
            uu = self._cx + self._fx * vc[0] / vc[2]
            vv = self._cy - self._fy * vc[1] / vc[2]
            if not (0 <= uu < self.ancho and 0 <= vv < self.alto):
                continue
            radio = 10 if nombre == "Luna" else 6
            cv2.circle(img, (int(uu), int(vv)), radio, _COLOR_PLANETA, -1)
            if etiquetas:
                cv2.putText(img, nombre, (int(uu) + 9, int(vv) - 7),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                            _COLOR_ETIQUETA, 1, cv2.LINE_AA)

        # --- etiquetas de las estrellas brillantes ---
        if etiquetas and len(idx):
            visibles = idx[mags[idx] < 2.0]
            for i in visibles:
                e = self.catalogo.estrellas[i]
                nombre = self._nombres_por_indice.get(e.id)
                if not nombre:
                    continue
                cv2.putText(img, nombre, (int(u[i]) + 4, int(v[i]) - 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                            _COLOR_ETIQUETA, 1, cv2.LINE_AA)

        # Estética de post-proceso (fondo + resplandor). La estética "plano"
        # devuelve la imagen sin cambios, así que no se calcula el fondo.
        return aplicar(img, self.estetica,
                       self._fondo_estetica() if self.estetica != "plano"
                       else None)
