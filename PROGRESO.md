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

- **Fase 6 — Astrometría: COMPLETADA y VALIDADA por el usuario.**
  - **Catálogo:** Yale Bright Star Catalog (CDS V/50) en `data/catalogo/bsc5.dat`;
    8.404 estrellas con mag ≤ 6.5 (el BSC completo tiene 9.110). HYG v3 no era
    descargable desde esta red (el sitio oficial sirve HTML); el cargador acepta
    formatos (`formato="bsc"`, reservado `"hyg"`) — ADR-005 actualizado.
    `skyrender/catalogo.py`: `Estrella`/`Catalogo`, vectores ecuatoriales J2000,
    búsqueda por nombre (el BSC incluye el número Flamsteed, p. ej. "21Alp And").
  - `skyrender/astro.py`: precesión J2000→fecha con la matriz `t.M` de skyfield
    (vectorizada, sin efemérides); matriz ecuatorial→horizontal (fórmulas de
    Meeus, columnas = imagen de los ejes ecuatoriales); LST; matriz de vista de
    cámara (rumbo/inclinación/roll); ubicación persistida en `data/ubicacion.json`.
  - `skyrender/demo_astro.py`: alt/az del cielo en un instante/lugar, compara
    contra skyfield y lista las más brillantes visibles.
  - Efemérides `de421.bsp` descargadas a `data/models/` (Fase 7 + referencia de
    los tests). `tools/download_models.py` ahora descarga hand_landmarker,
    de421 y el catálogo (con descompresión del gzip del CDS).
  - Tests: +14 → **55/55 en verde**. Precisión: 0.006° frente a skyfield;
    Polaris a alt 9.62° az 0.5° para lat 10N (alt ≈ latitud).
  - **Ubicación configurada (2026-08-10):** `data/ubicacion.json` =
    lat **9.66124**, lon **-68.58268** (Puerto Cabello, Venezuela), proporcionada
    por Matheus. La demo ya sale con esa posición: Polaris a alt 10.17° az 359.6°
    (alt ≈ latitud ✓), Betelgeuse a alt 82° az 106° (casi el cénit), Sirius a
    alt 56.9° az 142.8°, diferencia máxima frente a skyfield 0.006°.
  - **Validación de Matheus (2026-08-10):** comparó contra Stellarium y la
    comparación quedó confirmada (Estrella Polar y Orión coinciden con la demo).

- **Fase 5 — Calibración: COMPLETADA y VALIDADA por el usuario.**
  - Protocolo ampliado: `{"tipo":"calibrar","rumbo":...}` — el rumbo actual del
    celular se declara como el norte (0). El offset se calcula en el servidor
    (`rumbo_efectivo = (rumbo_celular − offset) mod 360`).
  - `compass.py`: `CompassState.calibrar()` calcula el offset, lo persiste en
    `data/calibracion.json` (ignorado en git) y lo carga al arrancar. La última
    lectura guardada se reajusta al calibrar.
  - `web.py`: `/estado` y `/monitor` exponen `calibrado`; el WebSocket distingue
    orientación de calibración.
  - `celular.html`: botón "Calibrar al norte" (envía el último rumbo absoluto).
  - `panel.html`: muestra "Calibrado · en vivo" cuando hay offset aplicado.
  - Tests: +6 → **38/38 en verde**. Verificación de integración sobre el
    servidor: orientación 50 → calibrar → rumbo 0; orientación 60 → rumbo 10
    (offset aplicado). Commit pendiente de validación y autorización.
  - **Validación de Matheus (2026-08-10):** apuntó al norte magnético, pulsó
    "Calibrar al norte" y el panel marcó 0 con el desfase estable → validado.

- **Fase 7 — Render del cielo: COMPLETADA y VALIDADA por el usuario.**
  - `skyrender/render.py`: clase `SkyRenderer` que proyecta las ~8.404 estrellas
    del catálogo BSC a píxeles con proyección perspectiva, incluyendo precesión
    cacheada (recálculo cada ~6 horas), culling del horizonte (alt > 0) y
    caché de planetas (~1/min). Tamaño y brillo de los puntos según la magnitud;
    las ~20 estrellas más brillantes llevan círculos de halo y etiquetas con
    nombres propios (Sirio, Betelgeuse, Vega, etc.).
  - `skyrender/constelaciones.py`: 17 constelaciones visibles desde lat 10°N
    (Osa Mayor/Menor, Orión, Tauro, Géminis, Leo, Casiopea, Lira, Águila,
    Cisne, Escorpio, Sagitario, Andrómeda, Pegaso, Cruz del Sur, Can Mayor,
    Carina), ~80 segmentos de líneas; búsqueda por designación normalizada
    (resuelve componentes del BSC como "41Gam1Leo" → "Gam Leo").
  - `skyrender/demo_render.py`: ventana 1280×720 con cielo en tiempo real,
    rumbo/inclinación interactiva (flechas), FOV ajustable (+/-) y contador FPS;
    modo `--sin-ventana` para benchmarks.
  - Tests: +9 → **64/64 en verde**. Medido en la laptop:521 FPS en cálculo
    puro (sin presentación). Capturas de referencia guardadas en
    `docs/capturas-fase7/` (Polaris + Triángulo de Verano con etiquetas).
  - `skyrender/__init__.py` y `catalogo.py` actualizados (buscar_designacion,
    exports nuevos).
  - **Mejoras visuales (2026-08-10, a petición de Matheus):** estrellas de fondo
    más brillantes (compresión con raíz cuadrada: mag 6.5 ≈ 32, mag 2 ≈ 255),
    26 constelaciones con ~120 segmentos y líneas más sutiles
    `_COLOR_CONSTELACION = (130, 125, 90)` en BGR.
  - **Brillo parametrizable (2026-08-10):** `SkyRenderer(brillo_factor=2.5)`
    por defecto (valor que prefirió Matheus); se puede ajustar en caliente
    cambiando `renderer.brillo_factor` entre frames. La demo expone
    `--brillo FACTOR` y las teclas `[` / `]` (0.1 a 3.0).
  - **Modos de gesto (ADR-004, confirmado por Matheus):** el render ya distingue
    `etiquetas=True/False`. El modo L mostrará el cielo sin nombres y el modo
    MANO_COMPLETA con nombres (Fase 9 conectará el gesto al render).
  - Tests de brillo añadidos → **66/66 en verde**.
  - **Validación de Matheus (2026-08-10):** probó la demo interactiva y aprobó
    el aspecto del cielo con brillo 2.5 → validado visualmente.

## Historial de fases

| Fase | Descripción | Estado |
|---|---|---|
| 0 | Infraestructura y entorno | Hecho |
| 1 | Captura de cámara | Hecho (validado por el usuario) |
| 2 | Detección de manos y marco | Hecho (validado por el usuario) |
| 3 | Servidor brújula plan A (WiFi + HTTPS) | Hecho (validado por el usuario) |
| 4 | Plan B (USB + adb reverse) | Pendiente |
| 5 | Calibración | Hecho (validado por el usuario) |
| 6 | Astrometría | Hecho (validado por el usuario vs Stellarium) |
| 7 | Render del cielo | Hecho (validado por el usuario; brillo 2.5 por defecto) |
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
