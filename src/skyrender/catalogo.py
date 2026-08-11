"""Catálogo de estrellas como vectores unitarios ecuatoriales (Fase 6).

El PLAN propone HYG v3 o Hipparcos. HYG v3 no está disponible como descarga
directa desde esta red (el sitio oficial sirve páginas HTML), así que el
catálogo de trabajo es el **Yale Bright Star Catalog** (CDS V/50): ~9.110
estrellas hasta magnitud ~6.5, es decir el mismo rango que el filtro
`mag <= 6.5` (~9.000 estrellas) del HYG. El cargador está preparado para
ampliarse a otros formatos (`formato="hyg"`).

Formato del archivo `bsc5.dat` (columnas fijas, ver `data/catalogo/ReadMe`)::

    1-  4  I4    HR     Harvard Revised (Bright Star) number
    5- 14  A10   Name   Bayer/Flamsteed u otro nombre propio
    76- 83       RA J2000  (h, m, s.s  →  grados = (h + m/60 + s/3600)*15)
    84- 90       Dec J2000 (signo, d, m, s  →  grados)
    103-107 F5.2 Vmag   Magnitud visual
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
RUTA_CATALOGO = DATA_DIR / "catalogo" / "bsc5.dat"

# Columnas (1-indexadas, del ReadMe del CDS V/50).
_RA_H = slice(75, 77)     # bytes 76-77
_RA_M = slice(77, 79)     # bytes 78-79
_RA_S = slice(79, 83)     # bytes 80-83
_DEC_SIGNO = 83           # byte 84 (signo de la declinación)
_DEC_D = slice(84, 86)    # bytes 85-86
_DEC_M = slice(86, 88)    # bytes 87-88
_DEC_S = slice(88, 90)    # bytes 89-90
_VMAG = slice(102, 107)   # bytes 103-107
_HR = slice(0, 4)
_NOMBRE = slice(4, 14)


@dataclass
class Estrella:
    """Una estrella del catálogo, en coordenadas ecuatoriales J2000."""
    id: int            # número HR (Harvard Revised)
    nombre: str        # Bayer/Flamsteed u otro nombre propio ("" si no tiene)
    ra_deg: float      # ascensión recta J2000, grados (0-360)
    dec_deg: float     # declinación J2000, grados (-90..90)
    mag: float         # magnitud visual


@dataclass
class Catalogo:
    estrellas: list[Estrella]

    def __init__(self, estrellas: list[Estrella] | None = None) -> None:
        self.estrellas = estrellas or []

    @property
    def n(self) -> int:
        return len(self.estrellas)

    def vectores_ecuatoriales(self) -> np.ndarray:
        """Matriz [N,3] de vectores unitarios en el marco ICRS (J2000).

        x → equinoccio (RA=0, Dec=0), y → RA=90°, z → polo norte celeste.
        """
        if not self.estrellas:
            return np.zeros((0, 3), dtype=np.float64)
        ra = np.radians(np.array([e.ra_deg for e in self.estrellas]))
        dec = np.radians(np.array([e.dec_deg for e in self.estrellas]))
        return np.stack([
            np.cos(dec) * np.cos(ra),
            np.cos(dec) * np.sin(ra),
            np.sin(dec),
        ], axis=1)

    def nombres(self) -> list[str]:
        return [e.nombre for e in self.estrellas]

    def buscar(self, nombre: str) -> Optional[Estrella]:
        """Devuelve la estrella cuyo nombre contiene a `nombre` (sin cajas).

        En el BSC el campo Name puede incluir el número Flamsteed
        (p. ej. "21Alp And"), por eso se compara por subcadena.
        """
        objetivo = nombre.strip().lower()
        for e in self.estrellas:
            if e.nombre and objetivo in e.nombre.lower():
                return e
        return None

    def por_id(self, hr: int) -> Optional[Estrella]:
        for e in self.estrellas:
            if e.id == hr:
                return e
        return None

    @staticmethod
    def _clave_designacion(nombre: str) -> str:
        """Normaliza un nombre del BSC: solo letras, minúsculas.

        El BSC codifica las componentes como dígitos pegados a la letra
        Bayer (p. ej. "41Gam1Leo", "Alp1Cru"), así que "Gam Leo" y
        "41Gam1Leo" normalizan a la misma clave "gamleo".
        """
        return "".join(ch for ch in nombre.lower() if ch.isalpha())

    def buscar_designacion(self, designacion: str) -> Optional[Estrella]:
        """Busca por letra Bayer + constelación (p. ej. "Gam Leo").

        A diferencia de `buscar`, ignora el número de componente del BSC
        (Gamma-1 Leonis = "41Gam1Leo" responde a "Gam Leo").
        """
        clave = self._clave_designacion(designacion)
        for e in self.estrellas:
            if e.nombre and clave in self._clave_designacion(e.nombre):
                return e
        return None


def _parsear_bsc(texto: str, mag_limite: float) -> list[Estrella]:
    estrellas: list[Estrella] = []
    for linea in texto.splitlines():
        if len(linea) < 107:
            continue
        try:
            hr = int(linea[_HR])
            mag = float(linea[_VMAG])
            ra = 15.0 * (int(linea[_RA_H])
                         + int(linea[_RA_M]) / 60.0
                         + float(linea[_RA_S]) / 3600.0)
            signo = -1.0 if linea[_DEC_SIGNO] == "-" else 1.0
            dec = signo * (int(linea[_DEC_D])
                           + int(linea[_DEC_M]) / 60.0
                           + int(linea[_DEC_S]) / 3600.0)
        except (ValueError, IndexError):
            continue
        if mag > mag_limite:
            continue
        estrellas.append(Estrella(id=hr, nombre=linea[_NOMBRE].strip(),
                                  ra_deg=ra, dec_deg=dec, mag=mag))
    estrellas.sort(key=lambda e: e.mag)
    return estrellas


def cargar_estrellas(ruta: Path | str = RUTA_CATALOGO,
                     mag_limite: float = 6.5,
                     formato: str = "bsc") -> Catalogo:
    """Carga el catálogo desde un archivo de texto de columnas fijas.

    Solo el formato ``"bsc"`` (Bright Star Catalog) está implementado.
    `formato="hyg"` queda reservado para cuando el HYG v3 sea descargable.
    """
    if formato != "bsc":
        raise ValueError(f"Formato de catálogo no soportado: {formato!r}")
    ruta = Path(ruta)
    if not ruta.exists():
        raise FileNotFoundError(
            f"Catálogo de estrellas no encontrado: {ruta}. "
            "Ejecuta: python tools/download_models.py")
    texto = ruta.read_text(encoding="latin-1")
    return Catalogo(_parsear_bsc(texto, mag_limite))
