"""Servidor web/WebSocket de la brújula (Plan A, ADR-001).

Rutas:
- `/`        → página del celular (envía la orientación por /ws).
- `/panel`   → panel de la laptop (muestra el rumbo en tiempo real vía /monitor).
- `/estado`  → estado actual en JSON (para depuración/lectura externa).
- `/ws`      → WebSocket del celular: recibe {rumbo, inclinacion, roll, ts}.
- `/monitor` → WebSocket de observadores: recibe el estado a cada actualización.

Plan A: HTTPS con el certificado auto-firmado de tools/gen-cert.
"""

from __future__ import annotations

import json
import logging
import ssl
from pathlib import Path

from aiohttp import WSMsgType, web

from .compass import CompassState, parse_mensaje

log = logging.getLogger("portal.server")

STATIC_DIR = Path(__file__).resolve().parent / "static"
CERT_DIR = Path(__file__).resolve().parents[2] / "tools" / "gen-cert"


@web.middleware
async def _log_peticiones(request, handler):
    """Registra cada petición que recibe el servidor (diagnóstico de red)."""
    try:
        resp = await handler(request)
    except Exception:
        log.warning("PETICION %s %s -> EXCEPCION", request.method, request.path)
        raise
    log.info("PETICION %s %s -> %s (desde %s)", request.method, request.path,
             resp.status, request.remote)
    return resp


class BrújulaServer:
    def __init__(self, state: CompassState | None = None):
        self.state = state or CompassState()
        self._monitores: set = set()
        self.app = web.Application(middlewares=[_log_peticiones])
        self._setup_routes()

    def _setup_routes(self) -> None:
        self.app.router.add_get("/", self._pagina_celular)
        self.app.router.add_get("/panel", self._pagina_panel)
        self.app.router.add_get("/estado", self._estado_json)
        self.app.router.add_get("/ws", self._ws_celular)
        self.app.router.add_get("/monitor", self._ws_monitor)

    # --- páginas estáticas -------------------------------------------------

    async def _pagina_celular(self, request: web.Request) -> web.Response:
        return web.Response(text=(STATIC_DIR / "celular.html").read_text("utf-8"),
                            content_type="text/html")

    async def _pagina_panel(self, request: web.Request) -> web.Response:
        return web.Response(text=(STATIC_DIR / "panel.html").read_text("utf-8"),
                            content_type="text/html")

    async def _estado_json(self, request: web.Request) -> web.Response:
        datos = self.state.get().to_dict()
        datos["fresh"] = self.state.fresh
        return web.json_response(datos)

    # --- WebSockets --------------------------------------------------------

    async def _ws_celular(self, request: web.Request) -> web.WebSocketResponse:
        """Recibe orientación del celular a 30-60 Hz y la difunde a /monitor."""
        ws = web.WebSocketResponse(max_msg_size=4096)
        await ws.prepare(request)
        try:
            async for msg in ws:
                if msg.type != WSMsgType.TEXT:
                    continue
                try:
                    datos = json.loads(msg.data)
                except json.JSONDecodeError:
                    continue
                orientacion = parse_mensaje(datos)
                if orientacion is not None:
                    self.state.update(orientacion)
                    await self._difundir_estado()
        finally:
            pass  # el cierre lo maneja aiohttp
        return ws

    async def _ws_monitor(self, request: web.Request) -> web.WebSocketResponse:
        """Retransmite el estado actual a los paneles (laptop)."""
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self._monitores.add(ws)
        try:
            await ws.send_json(self._estado_publico())
            async for msg in ws:
                if msg.type in (WSMsgType.ERROR, WSMsgType.CLOSE):
                    break
        finally:
            self._monitores.discard(ws)
        return ws

    # --- internos ----------------------------------------------------------

    def _estado_publico(self) -> dict:
        datos = self.state.get().to_dict()
        datos["fresh"] = self.state.fresh
        return datos

    async def _difundir_estado(self) -> None:
        payload = self._estado_publico()
        for ws in list(self._monitores):
            if ws.closed:
                self._monitores.discard(ws)
                continue
            try:
                await ws.send_json(payload)
            except (ConnectionResetError, RuntimeError):
                self._monitores.discard(ws)


def _ssl_context() -> ssl.SSLContext:
    cert = CERT_DIR / "cert.pem"
    key = CERT_DIR / "key.pem"
    if not (cert.exists() and key.exists()):
        raise FileNotFoundError(
            "Faltan los certificados del Plan A. Ejecuta primero: "
            "python tools/gen-cert/gen_cert.py"
        )
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(str(cert), str(key))
    return ctx


async def iniciar_servidor(host: str = "0.0.0.0", port: int = 8080,
                           tls: bool = True, state: CompassState | None = None):
    """Crea, enlaza y arranca el servidor. Devuelve (runner, site)."""
    servidor = BrújulaServer(state=state)
    runner = web.AppRunner(servidor.app)
    await runner.setup()
    ssl_ctx = _ssl_context() if tls else None
    site = web.TCPSite(runner, host, port, ssl_context=ssl_ctx)
    await site.start()
    scheme = "https" if tls else "http"
    log.info("Brújula servidor activo: %s://%s:%s  (panel en /panel)", scheme, host, port)
    return runner, site
