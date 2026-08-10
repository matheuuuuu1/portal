"""Punto de entrada del servidor de la brújula.

Uso:
    python -m server                      # Plan A: HTTPS en 0.0.0.0:8080
    python -m server --no-tls             # Plan B (Fase 4): HTTP sin certificado
    python -m server --port 8081 --tls
"""

import argparse
import asyncio
import logging

from .web import iniciar_servidor


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(
        description="Servidor de la brújula del celular (ADR-001).")
    parser.add_argument("--host", default="0.0.0.0",
                        help="Interfaz donde escuchar (0.0.0.0 = todas).")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--tls", action="store_true", default=True,
                        help="HTTPS con certificado auto-firmado (Plan A).")
    parser.add_argument("--no-tls", dest="tls", action="store_false",
                        help="HTTP plano (Plan B, Fase 4).")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")

    async def _run() -> None:
        runner, site = await iniciar_servidor(
            host=args.host, port=args.port, tls=args.tls)
        try:
            await asyncio.Event().wait()  # hasta Ctrl+C
        finally:
            await runner.cleanup()

    try:
        asyncio.run(_run())
    except KeyboardInterrupt:
        print("\nServidor detenido.")


if __name__ == "__main__":
    main()
