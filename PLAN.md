# PLAN — Portal al Cielo

Objetivo de rendimiento global: **30 FPS a 720p** en Dell Latitude 5320 (Intel 11.ª gen, Iris Xe). Objetivo definitivo (ADR-007): la cámara web probablemente limita a 30 FPS, así que no se persigue 60 FPS.

## Orden y dependencias

```
F0 ── F1 ── F2 ────────────────── F8 ── F9 ── F11
           └──────────────────────┘         ^
F3 ── F5 ── F6 ── F7 ───────────────────────┘
F4 (en paralelo con F3)
F10 (después de F7; recorre F8 y F9)
```

- F1 → F2 → F8: captura, manos y composición.
- F3 → F5 → F6 → F7 → F8: brújula, calibración, astrometría, render y composición.
- F4 se puede hacer en paralelo con F3 (plan B de transporte).
- F10 (optimización) se hace después de tener el render y la composición funcionando.

## Fase 0 — Infraestructura y entorno

- Tareas:
  - Crear el repositorio, el entorno virtual y `requirements.txt` (`opencv-python`, `mediapipe`, `numpy`, `aiohttp`, `skyfield`).
  - Dejar el esqueleto de paquetes de `src/` importable.
- Hecho cuando: `pip install` funciona y los módulos de `src` importan sin errores.

## Fase 1 — Captura de cámara

- Tareas: abrir la cámara web y mostrar el feed a 720p con un contador de FPS en pantalla.
- Hecho cuando: el feed se muestra estable a 30 FPS en el hardware objetivo.

## Fase 2 — Detección de manos y marco

- Tareas:
  - MediaPipe Hands: landmarks de pulgar/índice/medio por mano y lateralidad.
  - Construcción del cuadrilátero con 4 puntos.
  - Suavizado de landmarks y validación de degeneración (área mínima, orden de vértices).
  - Selección del modo según el par de dedos (L vs V).
- Hecho cuando: se dibuja el cuadrilátero en vivo y el modo cambia según el gesto sin parpadeos.

## Fase 3 — Servidor brújula plan A (WiFi + HTTPS)

- Tareas:
  - Servidor aiohttp que sirve `/` (página del celular) y `/ws` (WebSocket).
  - Página del celular con DeviceOrientation API (`requestPermission`) que envía `{rumbo, inclinacion, roll, ts}` a 30–60 Hz.
  - Script `tools/gen-cert` para generar el certificado auto-firmado una sola vez.
  - Redactar `docs/configuracion-celular.md` (plan A, nivel de detalle 8/10).
- Hecho cuando: la laptop muestra en tiempo real el rumbo/inclinación del Tecno Spark 10C a ≥30 Hz por WiFi con HTTPS y el flag de Chrome activado.

## Fase 4 — Plan B (USB + adb reverse)

- Tareas: documentar la activación de la Depuración USB, el comando `adb reverse tcp:8080 tcp:8080` y la apertura de `http://localhost:8080` en el celular. Verificar sin HTTPS.
- Hecho cuando: el flujo completo de brújula funciona por cable.

## Fase 5 — Calibración

- Tareas: botón **"Calibrar"** en la página; cálculo del offset en el servidor (`rumbo_efectivo = (rumbo_celular − offset) mod 360`); persistencia opcional del offset.
- Hecho cuando: apuntando al norte magnético y pulsando Calibrar, la app muestra rumbo 0 y el desfase se mantiene estable.

## Fase 6 — Astrometría

- Tareas:
  - Descargar el catálogo (HYG v3 o Hipparcos) y filtrar a magnitud ≤ 6.5 (~9.000 estrellas).
  - Cargar las estrellas como vectores unitarios ecuatoriales.
  - Implementar la matriz de rotación ecuatorial → horizontal (con skyfield para el instante) y la matriz de vista de cámara.
  - Configurar la ubicación geográfica.
- Hecho cuando: para una fecha/lugar/rumbo conocidos, el conjunto y el orden de estrellas coincide con Stellarium (pruebas de regresión con la Estrella Polar y la constelación de Orión).

## Fase 7 — Render del cielo

- Tareas: dibujar estrellas (tamaño y brillo según magnitud), constelaciones (líneas), planetas (efemérides `de421.bsp`) y etiquetas opcionales. Proyección vectorizada con numpy.
- Hecho cuando: una ventana de prueba muestra el cielo de una dirección a ≥30 FPS @720p.

## Fase 8 — Composición

- Tareas: calcular la homografía desde las 4 esquinas del marco, aplicar `warpPerspective` a la imagen del cielo y mezclar con el feed de cámara.
- Hecho cuando: el cielo aparece dentro del marco y lo sigue sin descolgarse ni deformarse de forma visible.

## Fase 9 — Modos de gesto

- Tareas: modo L (pulgar + índice) sin nombres; modo V (índice + medio) con nombres de los objetos importantes; cambio suave entre modos.
- Hecho cuando: cambiar el gesto cambia el modo de forma fiable y rápida, sin parpadeos en las etiquetas.

## Fase 10 — Optimización y robustez

- Tareas:
  - Benchmark en la Iris Xe (FPS, uso de CPU).
  - Mitigaciones si no se alcanzan los 30 FPS: reducir la resolución de la imagen del cielo a 540p, caché de la matriz de rotación ecuatorial → horizontal (recalcular solo cada 1–2 minutos), y pre-render opcional de la esfera celeste completa como textura rotada según el tiempo sidéreo (ver ARQUITECTURA, "Estrategia de precomputación y caché").
  - Manejo de pérdida de manos y de marco degenerado (mensaje en pantalla, sin cuelgues).
- Hecho cuando: 30 FPS sostenidos durante 10 minutos sin bloqueos, con aviso claro cuando no hay manos formando el marco.

## Fase 11 — Integración final y prueba de usuario

- Tareas: inicio de la aplicación con un solo comando; prueba completa del flujo guiado (configuración del celular → calibración → uso); documentación final con capturas reales.
- Hecho cuando: Matheus completa el flujo de principio a fin sin intervención del desarrollador.

## Notas de rendimiento

- El render del cielo es el cuello de botella previsible (proyección de ~9.000 estrellas + warp). Por eso se diseña vectorizado (F6/F7) y con mitigaciones explícitas (F10).
- MediaPipe en CPU suele consumir menos de 30 ms por frame; la detección se puede hacer a resolución reducida y sobreescalar los landmarks si hace falta.
