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

- **Fase 2 — Detección de manos y marco: EN CURSO (siguiente).**
  - Tareas: MediaPipe Hands (pulgar/índice/medio + lateralidad), cuadrilátero
    de 4 puntos, suavizado, validación de degeneración y selección de modo.
  - Hecho cuando: el cuadrilátero se dibuja en vivo y el modo cambia según el
    gesto sin parpadeos.

## Historial de fases

| Fase | Descripción | Estado |
|---|---|---|
| 0 | Infraestructura y entorno | Hecho |
| 1 | Captura de cámara | Hecho (validado por el usuario) |
| 2 | Detección de manos y marco | En curso |
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
- En la Fase 2 hay que **verificar la API de MediaPipe 1.0.0** (Hands) antes
  de codificar: la API legacy `mp.solutions.hands` puede haber cambiado.
- `data/catalogo` y `tools/gen-cert` quedan con `.gitkeep` (vacías por diseño).
