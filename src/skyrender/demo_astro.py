"""Demo de la Fase 6: estrellas del BSC proyectadas al horizonte local.

Uso::

    python -m skyrender.demo_astro [--lat GRADOS] [--lon GRADOS]
                                   [--fecha 'YYYY-MM-DD HH:MM[:SS]'] [--rumbo GRADOS]

La ubicación se toma de `--lat/--lon` si se pasan, o de `data/ubicacion.json`
si existe. Imprime la comparación del pipeline propio contra skyfield para
estrellas de referencia (Polaris, Alp And, Betelgeuse, Rigel, Sirius) y las
estrellas más brillantes visibles.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

import numpy as np
from skyfield.api import load

from .astro import (altaz_con_skyfield, altaz_desde_horizontal, aplicar_matriz,
                    cargar_ubicacion, lst_grados, matriz_horizontal,
                    precesionar_j2000)
from .catalogo import RUTA_CATALOGO, cargar_estrellas

# Designaciones del BSC: Polaris="1Alp UMi", Betelgeuse="58Alp Ori",
# Rigel="19Bet Ori", Sirius="9Alp CMa".
REFERENCIAS = ["Alp UMi", "Alp And", "Alp Ori", "Bet Ori", "Alp CMa"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Demo de astrometría (Fase 6)")
    parser.add_argument("--lat", type=float, help="latitud en grados (N+)")
    parser.add_argument("--lon", type=float, help="longitud en grados (E+)")
    parser.add_argument("--fecha",
                        help="instante 'YYYY-MM-DD HH:MM[:SS]' (UTC); "
                             "por defecto: ahora")
    args = parser.parse_args()

    ubicacion = cargar_ubicacion()
    if args.lat is not None and args.lon is not None:
        lat, lon = args.lat, args.lon
    elif ubicacion is not None:
        lat, lon = ubicacion.lat, ubicacion.lon
    else:
        print("Falta la ubicación: pasa --lat/--lon o crea data/ubicacion.json")
        return 2

    if args.fecha:
        formato = "%Y-%m-%d %H:%M:%S" if len(args.fecha) > 16 else "%Y-%m-%d %H:%M"
        dt = datetime.strptime(args.fecha, formato).replace(tzinfo=timezone.utc)
    else:
        dt = datetime.now(timezone.utc)

    ts = load.timescale()
    t = ts.from_datetime(dt)

    catalogo = cargar_estrellas(RUTA_CATALOGO)
    print(f"Catálogo: {catalogo.n} estrellas (mag <= 6.5)")
    if catalogo.n == 0:
        print("Catálogo vacío. ¿Existe data/catalogo/bsc5.dat?")
        return 2

    ra_j = np.array([e.ra_deg for e in catalogo.estrellas])
    dec_j = np.array([e.dec_deg for e in catalogo.estrellas])

    # --- pipeline propio: precesión + matriz horizontal ---
    ra_f, dec_f = precesionar_j2000(ra_j, dec_j, t)
    ra = np.radians(ra_f)
    dec = np.radians(dec_f)
    v_eq = np.stack([np.cos(dec) * np.cos(ra),
                     np.cos(dec) * np.sin(ra),
                     np.sin(dec)], axis=1)
    lst = lst_grados(lon, float(t.gast))
    M = matriz_horizontal(lat, lst)
    v_horiz = aplicar_matriz(M, v_eq)
    alt, az = altaz_desde_horizontal(v_horiz)

    # --- referencia con skyfield (parte de las RA/Dec J2000 originales) ---
    alt_ref, az_ref = altaz_con_skyfield(ra_j, dec_j, lat, lon, t)

    print(f"Ubicación: lat {lat:.4f}° lon {lon:.4f}° | instante {t.utc_strftime()} "
          f"UTC | LST {lst:.3f}°")
    print("\nEstrellas de referencia (alt/az propios vs skyfield):")
    for nombre in REFERENCIAS:
        e = catalogo.buscar(nombre)
        if e is None:
            print(f"  {nombre:12s} no encontrada en el catálogo")
            continue
        idx = catalogo.estrellas.index(e)
        print(f"  {nombre:12s} alt {alt[idx]:7.2f}° az {az[idx]:7.2f}°  |  "
              f"skyfield alt {alt_ref[idx]:7.2f}° az {az_ref[idx]:7.2f}°")

    max_err = float(np.max(np.abs(alt - alt_ref)))
    print(f"\nDiferencia máxima en alt frente a skyfield: {max_err:.3f}°")

    # --- las más brillantes visibles (alt > 10°) ---
    visibles = np.where(alt > 10.0)[0]
    visibles = sorted(visibles, key=lambda i: catalogo.estrellas[i].mag)
    print(f"\n{min(10, len(visibles))} más brillantes visibles (alt > 10°):")
    for i in visibles[:10]:
        e = catalogo.estrellas[i]
        nombre = e.nombre or f"HR{e.id}"
        print(f"  {nombre:14s} mag {e.mag:4.1f}  alt {alt[i]:6.1f}°  az {az[i]:6.1f}°")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
