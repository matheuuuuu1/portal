# PROGRESO — Portal al Cielo

Seguimiento de la implementación del `PLAN.md`. La entrada de "Estado actual"
es el punto de retoma para la próxima sesión.

## Estado actual (2026-08-10)

- **Fase 0 — Infraestructura y entorno: COMPLETADA.**
  - Repositorio git inicializado (rama `main`); primer commit realizado.
  - Entorno virtual `.venv/` creado con **Python 3.14.6**.
  - `requirements.txt` con las 5 dependencias del ADR-002.
  - `pyproject.toml` con layout `src/`; `pip install -e .` deja `app`,
    `handtracking`, `skyrender`, `compositor` y `server` importables.
  - Verificado desde un directorio neutro: dependencias + paquetes importan
    sin errores (criterio de "hecho" de la Fase 0).

- **Fase 1 — Captura de cámara: COMPLETADA y VALIDADA por el usuario.**
  - `src/app/capture.py`: clase `CameraCapture` (720p, redimensiona si hace
    falta, backend por defecto).
  - `src/app/demo_capture.py`: feed con contador de FPS (q/ESC para salir).
  - Medido: cámara entrega **1280x720 nativo a ~30 fps**. Matheus confirmó
    que ve el feed estable y bien → criterio de "hecho" cumplido.
  - Hallazgo importante: con DirectShow (CAP_DSHOW) la captura baja a ~10 fps;
    con el backend por defecto se logran los 30 fps. Queda documentado en
    `capture.py`.

- **Fase 2 — Detección de manos y marco: COMPLETADA y VALIDADA por el usuario.**
  - **API**: MediaPipe 1.0.0 eliminó `mp.solutions.hands`; se usa la Tasks API
    (`HandLandmarker`), que requiere el modelo externo `hand_landmarker.task`
    (7.8 MB) descargado a `data/models/` con `tools/download_models.py`.
  - `src/handtracking/`: `detector.py`, `gesture.py` (modos L y MANO_COMPLETA),
    `quadrilateral.py`, `smoothing.py`, `pipeline.py` (debounce de modo),
    `demo_hands.py`.
  - Tests: `tests/test_gesture.py`, `tests/test_quadrilateral.py`,
    `tests/test_smoothing.py` → en verde. Commit `6703fd8`.
  - **Gesto (ADR-004) — interpretación VALIDADA por el usuario 2026-08-10:**
    - Modo **L** (pulgar + índice, medio plegado): sin nombres.
    - Modo **MANO_COMPLETA** (pulgar + índice + medio, palma abierta): con
      nombres. Sustituye al antiguo modo V (índice + medio).
    - Estabilización: factor del pulgar 1.10, margen 0.035, debounce de 3
      frames. El usuario confirmó que "mucho mejor".

- **Fase 3 — Servidor brújula Plan A (WiFi + HTTPS): COMPLETADA y VALIDADA por el usuario.**
  - `tools/gen-cert/gen_cert.py`: certificado auto-firmado con `cryptography`
    (Python puro, **sin depender de openssl en el PATH** — la primera versión
    falló en PowerShell del usuario) → key.pem y cert.pem (ignorados en git).
    Certificado generado y verificado.
  - `src/server/`: `compass.py` (estado compartido + validación del protocolo),
    `web.py` (aiohttp: `/`, `/panel`, `/estado`, `/ws`, `/monitor`),
    `__main__.py` (`python -m server`), `static/celular.html` (DeviceOrientation
    API, envía a 30-60 Hz), `static/panel.html` (brújula en la laptop).
  - Tests: `tests/test_compass.py` → **32/32 en verde** en total.
  - Integración verificada sin celular: HTTPS funciona, `/estado` devuelve JSON,
    el WebSocket `/ws` actualiza el estado y `/monitor` lo retransmite (rumbo
    212.3° reflejado).
  - **Validación real con el Tecno Spark 10C: CONFIRMADA por el usuario**
    (2026-08-10): con `https://IP:8080` en el celular (flag de Chrome + aceptar
    el cert auto-firmado) y el sensor activado, el panel `/panel` sigue el rumbo
    en vivo. "Si funciona todo".
  - **Corrección durante la validación:** Chrome/Android entrega el rumbo
    absoluto (magnetómetro) solo por el evento `deviceorientationabsolute`, no
    por `deviceorientation` (que llega con `absolute:false` y se descartaba →
    el servidor quedaba en `fresh:false` sin datos). `celular.html` ahora usa
    `deviceorientationabsolute` cuando existe y avisa en pantalla si el rumbo
    absoluto no llega. El servidor recibía la orientación correctamente desde
    el primer momento.
  - **Corrección de diagnóstico:** `web.py` añadió un middleware de registro de
    peticiones (`PETICION GET /ruta -> código`) porque aiohttp con `AppRunner`
    no loguea peticiones por defecto. Sirvió para confirmar qué conecta.
  - **Incidentes documentados (docs/configuracion-celular.md):** `ERR_EMPTY_RESPONSE`
    si se escribe `http://` (el servidor es solo TLS); advertencia del cert
    auto-firmado (Avanzado → Continuar); firewall de Windows (regla
    `netsh ... localport=8080`); QuickEdit de la consola de Windows pausa el
    servidor si se hace clic en la ventana mientras corre.

## Historial de fases

| Fase | Descripción | Estado |
|---|---|---|
| 0 | Infraestructura y entorno | Hecho |
| 1 | Captura de cámara | Hecho (validado por el usuario) |
| 2 | Detección de manos y marco | Hecho (validado por el usuario) |
| 3 | Servidor brújula plan A (WiFi + HTTPS) | Hecho (validado por el usuario) |
| 4 | Plan B (USB + adb reverse) | Pendiente |
| 5 | Calibración | Pendiente |
| 6 | Astrometría | Pendiente |
| 7 | Render del cielo | Pendiente |
| 8 | Composición | Pendiente |
| 9 | Modos de gesto | Pendiente |
| 10 | Optimización y robustez | Pendiente |
| 11 | Integración final y prueba de usuario | Pendiente |

## Notas de implementación

- **Python 3.14.6**: todas las librerías tienen wheel para 3.14 (mediapipe
  1.0.0 incluido). No hace falta bajar a otra versión de Python.
- **Doble OpenCV**: mediapipe 1.0.0 arrastra `opencv-contrib-python` y el
  requirements pide `opencv-python`; ambos 5.0.0.93 quedaron instalados y
  `import cv2` funciona (misma versión, sin conflicto visible). Si en fases
  posteriores da problemas, se elimina uno de los dos.
- **MediaPipe 1.0.0**: la API legacy `mp.solutions.hands` fue ELIMINADA; se
  usa la Tasks API (`HandLandmarker`) con el modelo `hand_landmarker.task`
  descargado por `tools/download_models.py`.
- **`cryptography`** se añadió a `requirements.txt` (Fase 3) para generar el
  certificado auto-firmado sin depender de openssl en el PATH.
- `data/catalogo` y `tools/gen-cert` quedan con `.gitkeep` (vacías por diseño).
