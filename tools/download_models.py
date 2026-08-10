"""Descarga los modelos y datos externos que el proyecto necesita.

Los binarios/archivos grandes no se versionan en git (ver .gitignore):
se descargan una sola vez con este script. Algunos dependen de la fase del
PLAN que esté en curso:

- hand_landmarker.task  -> Fase 2 (detección de manos, MediaPipe Tasks API)
- de421.bsp             -> Fase 6/7 (efemérides de planetas, skyfield)
- catálogo de estrellas  -> Fase 6 (Bright Star Catalog, CDS V/50)

Nota sobre el catálogo: el PLAN propone HYG v3 o Hipparcos. HYG v3 no está
disponible como descarga directa desde la red de desarrollo (el sitio oficial
sirve páginas HTML), así que se usa el Yale Bright Star Catalog, que cubre el
mismo rango (estrellas hasta mag ~6.5). El cargador de skyrender acepta otros
formatos si más adelante se consigue el HYG.

Uso:
    python tools/download_models.py          # descarga lo que falte
    python tools/download_models.py --only hand_landmarker
"""

import argparse
import gzip
import sys
from pathlib import Path
from urllib.request import urlretrieve

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"

# name -> (url, destino relativo a data/, post-procesado opcional)
MODELS = {
    "hand_landmarker": (
        "https://storage.googleapis.com/mediapipe-models/"
        "hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task",
        "models/hand_landmarker.task",
        None,
    ),
    "de421": (
        "https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de421.bsp",
        "models/de421.bsp",
        None,
    ),
    "catalogo": (
        "https://cdsarc.cds.unistra.fr/ftp/cats/V/50/catalog.gz",
        "catalogo/catalog.gz",
        "catalogo/bsc5.dat",  # descomprime catalog.gz -> bsc5.dat
    ),
}


def download(name: str) -> Path:
    url, rel, post = MODELS[name]
    dest = DATA_DIR / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        print(f"[ok] {name} ya existe: {dest.relative_to(PROJECT_ROOT)}")
    else:
        print(f"[..] descargando {name} desde {url}")
        urlretrieve(url, dest)
        size_mb = dest.stat().st_size / 1e6
        print(f"[ok] {name}: {size_mb:.1f} MB -> {dest.relative_to(PROJECT_ROOT)}")

    if post:
        final = DATA_DIR / post
        if not final.exists():
            print(f"[..] descomprimiendo {dest.name} -> {final.name}")
            with gzip.open(dest, "rb") as fin, open(final, "wb") as fout:
                fout.write(fin.read())
            print(f"[ok] {name}: {final.relative_to(PROJECT_ROOT)}")
    return dest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--only", choices=list(MODELS), default=None,
        help="Descargar solo un recurso (por defecto: todos).",
    )
    args = parser.parse_args(argv)

    names = [args.only] if args.only else list(MODELS)
    for name in names:
        try:
            download(name)
        except Exception as exc:  # noqa: BLE001 - reportar y seguir
            print(f"[error] {name}: {exc}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
