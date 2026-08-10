"""Astrometría: rotación ecuatorial (J2000) → horizontal local (Fase 6).

El cielo estrellado se calcula en el marco local del observador:
x → norte, y → este, z → cénit. La conversión se hace en dos pasos:

1. **Precesión** J2000 → fecha del instante, con skyfield (una vez por sesión).
2. **Matriz ecuatorial→horizontal**, construida con skyfield para el instante
   (tiempo sidéreo local + latitud) y aplicada de forma vectorizada con numpy.

Las fórmulas de alt/az son las estándar de Meeus, *Astronomical Algorithms*
(cap. 13), azimut desde el sur y convertido a azimut desde el norte. La matriz
se construye aplicando esa transformación a los tres ejes ecuatoriales, lo que
garantiza consistencia con las fórmulas y se verifica contra `skyfield` en los
tests.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

from skyfield.api import Star, load, wgs84

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
RUTA_UBICACION = DATA_DIR / "ubicacion.json"
RUTA_EFEMERIDES = DATA_DIR / "models" / "de421.bsp"

_PI = math.pi
_DEG = math.pi / 180.0


@dataclass
class Ubicacion:
    """Lugar de observación (la laptop / la cámara web)."""
    lat: float          # grados, norte positivo
    lon: float          # grados, este positivo
    nombre: str = ""

    def to_dict(self) -> dict:
        return {"lat": self.lat, "lon": self.lon, "nombre": self.nombre}


def cargar_ubicacion(ruta: Path | str = RUTA_UBICACION) -> Optional[Ubicacion]:
    """Carga la ubicación guardada, o None si no existe."""
    try:
        datos = json.loads(Path(ruta).read_text("utf-8"))
        return Ubicacion(lat=float(datos["lat"]), lon=float(datos["lon"]),
                         nombre=str(datos.get("nombre", "")))
    except (OSError, ValueError, KeyError, TypeError):
        return None


def guardar_ubicacion(ubicacion: Ubicacion,
                      ruta: Path | str = RUTA_UBICACION) -> None:
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    Path(ruta).write_text(json.dumps(ubicacion.to_dict()), encoding="utf-8")


def lst_grados(lon_deg: float, gast_horas: float) -> float:
    """Tiempo sidéreo local aparente en grados (este positivo)."""
    return (gast_horas * 15.0 + lon_deg) % 360.0


# ---------------------------------------------------------------------------
# Precesión J2000 → fecha (skyfield, vectorizada)
# ---------------------------------------------------------------------------

def precesionar_j2000(ra_deg, dec_deg, t):
    """Convierte RA/Dec J2000 (arrays de grados) al marco aparente del instante.

    Usa la matriz de precesión-nutación de skyfield (`t.M`), aplicada de forma
    vectorizada. No requiere efemérides. Devuelve (ra_deg, dec_deg).
    """
    ra = np.asarray(ra_deg, dtype=np.float64)
    dec = np.asarray(dec_deg, dtype=np.float64)
    v = np.stack([
        np.cos(np.radians(dec)) * np.cos(np.radians(ra)),
        np.cos(np.radians(dec)) * np.sin(np.radians(ra)),
        np.sin(np.radians(dec)),
    ], axis=1)
    return _de_vectores_a_radec(precesionar_vectores_j2000(v, t))


def precesionar_vectores_j2000(v_j2000, t) -> np.ndarray:
    """Precesiona vectores [N,3] de J2000 al marco aparente de `t`."""
    M = np.asarray(t.M, dtype=np.float64)
    return (M @ np.asarray(v_j2000, dtype=np.float64).T).T


def _de_vectores_a_radec(v) -> tuple[np.ndarray, np.ndarray]:
    x, y, z = v[:, 0], v[:, 1], v[:, 2]
    ra = np.degrees(np.arctan2(y, x)) % 360.0
    dec = np.degrees(np.arctan2(z, np.hypot(x, y)))
    return ra, dec


# ---------------------------------------------------------------------------
# Ecuatorial → horizontal
# ---------------------------------------------------------------------------

def _a_horizontal(ra_deg: float, dec_deg: float,
                  lat_deg: float, lst_deg: float) -> tuple[float, float, float]:
    """Alt/az de (ra, dec) y devuelve el vector (x, y, z) local N-E-cénit.

    Fórmulas de Meeus: azimut desde el sur (positivo hacia el oeste) y luego
    convertido a azimut desde el norte.
    """
    lat = lat_deg * _DEG
    dec = dec_deg * _DEG
    ha = (lst_deg - ra_deg) * _DEG
    sin_alt = math.sin(lat) * math.sin(dec) \
        + math.cos(lat) * math.cos(dec) * math.cos(ha)
    alt = math.asin(max(-1.0, min(1.0, sin_alt)))
    az_sur = math.atan2(math.sin(ha),
                        math.cos(ha) * math.sin(lat)
                        - math.tan(dec) * math.cos(lat))
    az_norte = az_sur + _PI
    x = math.cos(alt) * math.cos(az_norte)
    y = math.cos(alt) * math.sin(az_norte)
    z = math.sin(alt)
    return x, y, z


def matriz_horizontal(lat_deg: float, lst_deg: float) -> np.ndarray:
    """Matriz 3x3 que lleva vectores ecuatoriales al marco horizontal.

    Las columnas son la imagen de los ejes ecuatoriales:
    e1 = (RA=0, Dec=0), e2 = (RA=90°, Dec=0), e3 = (Dec=90°, polo norte).
    """
    e1 = _a_horizontal(0.0, 0.0, lat_deg, lst_deg)
    e2 = _a_horizontal(90.0, 0.0, lat_deg, lst_deg)
    e3 = _a_horizontal(0.0, 90.0, lat_deg, lst_deg)
    return np.array([e1, e2, e3], dtype=np.float64).T


def aplicar_matriz(M: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Aplica M (3x3) a vectores [N,3]. Devuelve [N,3]."""
    v = np.asarray(v, dtype=np.float64)
    return (M @ v.T).T


def matriz_vista_camara(rumbo_deg: float, inclinacion_deg: float,
                        roll_deg: float = 0.0) -> np.ndarray:
    """Matriz 3x3 del marco horizontal (N-E-cénit) al marco de la cámara.

    La cámara mira hacia (azimut=rumbo, altitud=inclinacion). En el marco de la
    cámara: z → dirección de apuntado (adelante), y → arriba de la imagen,
    x → derecha de la imagen. Las coordenadas de cámara de un vector `v` local
    son `M @ v`. El `roll` rota la imagen alrededor del eje de apuntado.
    """
    az = rumbo_deg * _DEG
    alt = inclinacion_deg * _DEG
    z_cam = np.array([math.cos(alt) * math.cos(az),
                      math.cos(alt) * math.sin(az),
                      math.sin(alt)], dtype=np.float64)
    cenit = np.array([0.0, 0.0, 1.0])
    y_cam = cenit - z_cam * float(np.dot(cenit, z_cam))
    n = np.linalg.norm(y_cam)
    y_cam = y_cam / n if n > 1e-12 else np.array([0.0, 1.0, 0.0])
    x_cam = np.cross(y_cam, z_cam)
    M = np.vstack([x_cam, y_cam, z_cam])
    if roll_deg:
        r = roll_deg * _DEG
        R = np.array([[math.cos(r), -math.sin(r), 0.0],
                      [math.sin(r), math.cos(r), 0.0],
                      [0.0, 0.0, 1.0]])
        M = R @ M
    return M


def altaz_desde_horizontal(v_horiz: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """De vectores [N,3] en el marco N-E-cénit a (alt_deg, az_deg).

    alt en grados (-90..90), az en grados desde el norte en sentido horario
    (0-360: 90 = este, 180 = sur, 270 = oeste).
    """
    v = np.asarray(v_horiz, dtype=np.float64)
    alt = np.degrees(np.arcsin(np.clip(v[:, 2], -1.0, 1.0)))
    az = np.degrees(np.arctan2(v[:, 1], v[:, 0])) % 360.0
    return alt, az


# ---------------------------------------------------------------------------
# Referencia con skyfield (para tests y depuración)
# ---------------------------------------------------------------------------

def altaz_con_skyfield(ra_deg, dec_deg, lat: float, lon: float, t,
                       ruta_efemerides: Path | str = RUTA_EFEMERIDES
                       ) -> tuple[np.ndarray, np.ndarray]:
    """alt/az de referencia usando skyfield (precesión + nutación incluidas).

    Requiere las efemérides `de421.bsp` (se descargan con
    `tools/download_models.py`). Es la referencia para validar el pipeline
    propio en los tests.
    """
    ruta = Path(ruta_efemerides)
    if not ruta.exists():
        raise FileNotFoundError(
            "Faltan las efemérides de421.bsp (referencia de skyfield). "
            "Descárgalas con tools/download_models.py")
    ra = np.asarray(ra_deg, dtype=np.float64)
    dec = np.asarray(dec_deg, dtype=np.float64)
    earth = load(str(ruta))["earth"]
    topos = earth + wgs84.latlon(lat, lon)
    alt = np.empty_like(ra)
    az = np.empty_like(ra)
    for i, (r, d) in enumerate(zip(ra, dec)):
        star = Star(ra_hours=r / 15.0, dec_degrees=d)
        aparente = topos.at(t).observe(star).apparent()
        alt_i, az_i, _ = aparente.altaz()
        alt[i] = alt_i.degrees
        az[i] = az_i.degrees % 360.0
    return alt, az
