"""Portal al Cielo — punto de entrada único (Fase 11).

Arranca el servidor de la brújula y la demo de composición en un solo
comando. El servidor corre en un hilo daemon con su propio event loop;
la demo (OpenCV) corre en el hilo principal.

Uso:

    portal                              # Plan A: HTTPS + demo
    portal --no-tls                     # Plan B: HTTP + demo
    portal --port 8081 --camera 0       # personalizar puerto y cámara
    portal --rumbo 180 --inclinacion 45 # orientación inicial

Todos los argumentos de la demo (flechas, brillo, estética, modo, etc.)
se pasan directamente al demo_compositor — consulta su ayuda con
``python -m compositor.demo_compositor --help``.
"""

from __future__ import annotations

import argparse
import asyncio
import socket
import sys
import threading
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parents[2] / "data"
_CERT_DIR = Path(__file__).resolve().parents[2] / "tools" / "gen-cert"


# -- prerequisites ------------------------------------------------------------

def _verificar_prerequisitos() -> list[str]:
    """Devuelve una lista de mensajes de error si falta algo critical."""
    errores = []
    modelo_manos = _DATA_DIR / "models" / "hand_landmarker.task"
    if not modelo_manos.exists():
        errores.append(
            f"Falta {modelo_manos.name}. "
            "Ejecuta: python tools/download_models.py")
    efemerides = _DATA_DIR / "models" / "de421.bsp"
    if not efemerides.exists():
        errores.append(
            f"Falta {efemerides.name}. "
            "Ejecuta: python tools/download_models.py")
    catalogo = _DATA_DIR / "catalogo" / "bsc5.dat"
    if not catalogo.exists():
        errores.append(
            f"Falta {catalogo.name}. "
            "Ejecuta: python tools/download_models.py")
    return errores


def _verificar_certificado(tls: bool) -> list[str]:
    """Devuelve error si falta el certificado y se pide TLS."""
    if not tls:
        return []
    errores = []
    for nombre in ("cert.pem", "key.pem"):
        if not (_CERT_DIR / nombre).exists():
            errores.append(
                f"Falta {_CERT_DIR / nombre}. "
                "Ejecuta: python tools/gen-cert/gen_cert.py")
    return errores


# -- servidor en hilo daemon --------------------------------------------------

def _arrancar_servidor(host: str, port: int, tls: bool) -> None:
    """Arranca el servidor de la brújula en un hilo daemon."""
    from server.web import iniciar_servidor

    async def _run():
        runner, _site = await iniciar_servidor(
            host=host, port=port, tls=tls)
        try:
            await asyncio.Event().wait()
        finally:
            await runner.cleanup()

    try:
        asyncio.run(_run())
    except Exception:
        pass  # el hilo muere con el proceso


def _obtener_ip_local() -> str:
    """Intenta obtener la IP local (no 127.0.0.1)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


# -- main ----------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Portal al Cielo — arranca servidor + demo (Fase 11)",
        add_help=True)
    # Args del servidor (solo los que el launcher necesita conocer).
    parser.add_argument("--host", default="0.0.0.0",
                        help="interfaz del servidor (def. 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8080,
                        help="puerto del servidor (def. 8080)")
    parser.add_argument("--tls", action="store_true", default=True,
                        help="HTTPS con certificado auto-firmado (Plan A)")
    parser.add_argument("--no-tls", dest="tls", action="store_false",
                        help="HTTP plano (Plan B, sin certificado)")
    # Todo lo demás se pasa al demo_compositor.
    server_args, demo_argv = parser.parse_known_args(argv)

    # --- prerequisites --------------------------------------------------------
    errores = _verificar_prerequisitos()
    errores += _verificar_certificado(server_args.tls)
    if errores:
        for e in errores:
            print(f"Error: {e}")
        return 1

    # --- ubicación ------------------------------------------------------------
    ubicacion = _DATA_DIR / "ubicacion.json"
    if not ubicacion.exists():
        print("Aviso: sin data/ubicacion.json; se usa lat 10, lon -68.")

    # --- servidor en hilo daemon ----------------------------------------------
    scheme = "https" if server_args.tls else "http"
    servidor_url = f"{scheme}://localhost:{server_args.port}"
    hilo_servidor = threading.Thread(
        target=_arrancar_servidor,
        args=(server_args.host, server_args.port, server_args.tls),
        daemon=True)
    hilo_servidor.start()

    ip = _obtener_ip_local()

    # --- instrucciones en terminal --------------------------------------------
    print()
    print("=" * 60)
    print("  Portal al Cielo")
    print("=" * 60)
    print()
    print(f"  Servidor: {scheme}://0.0.0.0:{server_args.port}")
    print(f"  Panel laptop: {scheme}://localhost:{server_args.port}/panel")
    print()
    print(f"  1. Abre {scheme}://{ip}:{server_args.port} en el celular")
    print("     (acepta el cert auto-firmado si es HTTPS)")
    print("  2. Activa el sensor de orientacion en la pagina")
    print("  3. Apunta al norte magnetico y pulsa 'Calibrar'")
    print("  4. Forma una ventana con ambas manos para ver el cielo")
    print()
    print("  Flechas: rumbo/inclinacion | n: etiquetas | e: estetica")
    print("  i: panel de info | c: medidor | m: modo | q/ESC: salir")
    print()
    print("=" * 60)
    print()

    # --- demo (hilo principal) ------------------------------------------------
    demo_argv_completed = ["--brujula", servidor_url] + list(demo_argv)
    from compositor.demo_compositor import run
    return run(argv=demo_argv_completed)


if __name__ == "__main__":
    raise SystemExit(main())
