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

- **Fase 2 — Detección de manos y marco: IMPLEMENTADA; falta re-validar el gesto.**
  - **API**: MediaPipe 1.0.0 eliminó `mp.solutions.hands`; se usa la Tasks API
    (`HandLandmarker`), que requiere el modelo externo `hand_landmarker.task`
    (7.8 MB) descargado a `data/models/` con `tools/download_models.py`.
  - `src/handtracking/`: `detector.py` (HandDetector), `gesture.py` (dedos
    extendidos + modo L/MANO_COMPLETA/NINGUNO), `quadrilateral.py` (4 esquinas
    ordenadas + validación de área mínima), `smoothing.py` (EMA),
    `pipeline.py` (HandPipeline con debounce de modo), `demo_hands.py`.
  - Tests: `tests/test_gesture.py`, `tests/test_quadrilateral.py`,
    `tests/test_smoothing.py` → **22/22 en verde**.
  - Rendimiento medido sin ventana: pipeline completo **31.2-31.8 fps**.
  - **Gesto (ADR-004) — interpretación VALIDADA por el usuario 2026-08-10:**
    - Modo **L** (pulgar + índice extendidos, medio PLEGADO): sin nombres.
    - Modo **MANO_COMPLETA** (pulgar + índice + medio extendidos, palma
      abierta): con nombres. Sustituye al antiguo modo V (índice + medio).
    - El usuario pidió estabilizar la L: se bajó el factor del pulgar de 1.15
      a 1.10 y el margen de extensión de 0.04 a 0.035, y se añadió un
      **debounce de 3 frames** en `HandPipeline` para que el modo no parpadee.
  - **Pendiente de Matheus:** ejecutar `python -m handtracking.demo_hands`,
    probar la L y la mano completa, y confirmar que ambas responden sin
    parpadeos (la demo muestra por mano P/I/M = 1/0 de dedos extendidos).

## Historial de fases

| Fase | Descripción | Estado |
|---|---|---|
| 0 | Infraestructura y entorno | Hecho |
| 1 | Captura de cámara | Hecho (validado por el usuario) |
| 2 | Detección de manos y marco | Implementada (falta validar visualmente) |
| 3 | Servidor brújula plan A (WiFi + HTTPS) | Pendiente |
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
- `data/catalogo` y `tools/gen-cert` quedan con `.gitkeep` (vacías por diseño).
