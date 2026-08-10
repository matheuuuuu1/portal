# DECISIONES — Registro de decisiones de diseño (ADR)

Formato breve: Contexto → Decisión → Alternativas descartadas → Consecuencias.

## ADR-001 — Brújula externa por celular Android

- **Contexto:** las laptops normales no traen magnetómetro. El acelerómetro da inclinación, pero el rumbo absoluto requiere magnetómetro.
- **Decisión:** el celular Android actúa de brújula con la DeviceOrientation API. Plan A: **WiFi + HTTPS** (certificado auto-firmado una vez + flag de Chrome "origen inseguro como seguro") con WebSocket a 30–60 Hz. Plan B de respaldo: **USB + Depuración USB + `adb reverse tcp:8080 tcp:8080`** (el celular entra a su propio `localhost:8080`, tratado como seguro por el navegador sin HTTPS).
- **Alternativas descartadas:** magnetómetro USB externo (hardware adicional, integración frágil) y apuntar manualmente el cielo (no es tiempo real).
- **Consecuencias:** se debe mantener una guía de configuración del celular con nivel de detalle 8/10 (`docs/configuracion-celular.md`). El celular validado (Tecno Spark 10C) tiene e-compass.

## ADR-002 — Stack Python

- **Contexto:** se necesita servidor web/WebSocket + astrometría + visión por computadora en el mismo proceso.
- **Decisión:** Python con aiohttp (servidor), skyfield (astrometría), numpy (proyección vectorizada), MediaPipe (manos) y OpenCV (captura/render).
- **Alternativas:** Node (astronomía más pobre; MediaPipe JS con límites de CPU) y C++ (esfuerzo mucho mayor, sin necesidad).
- **Consecuencias:** ecosistema de astrometría maduro; el rendimiento se logra con proyección vectorizada (no iterando por estrella).

## ADR-003 — Detección de manos con MediaPipe Hands

- **Contexto:** hay que detectar landmarks de ambas manos en tiempo real para formar el marco.
- **Decisión:** MediaPipe Hands (bindings oficiales de Python), con lateralidad (handedness) para asignar las esquinas izquierda/derecha del rectángulo.
- **Alternativas:** OpenPose (más pesado en CPU) y segmentación de fondo con OpenCV (no robusta).
- **Consecuencias:** buena relación robustez/rendimiento; los landmarks 4 (pulgar), 8 (índice) y 12 (medio) son la base de los dos modos de gesto.

## ADR-004 — Dos modos de gesto (VALIDADO Y ACTUALIZADO POR EL USUARIO el 2026-08-10)

- **Contexto:** el marco lo forman siempre dos manos y cada una aporta dos dedos (4 esquinas). El gesto de las manos puede cambiar el modo de visualización.
- **Decisión:** con **pulgar + índice** de cada mano (forma de L) y el **medio plegado**, se ven constelaciones y planetas **sin nombres**. Con la **mano completa** (pulgar + índice + medio extendidos, palma abierta, en ambos modos las esquinas del marco son pulgar + índice) se ven las mismas constelaciones y planetas, pero los **más importantes muestran su nombre**.
- **Nota:** el diseño original planteaba un modo V (índice + dedo medio), pero durante la implementación el usuario pidió sustituirlo por la mano completa porque le resultaba más natural de formar con ambas manos para armar el cuadro. Queda registrado como decisión validada.
- **Riesgo (mitigado):** al usar siempre pulgar + índice como esquinas, desapareció el riesgo del cuadrilátero casi degenerado del antiguo modo V. Queda la estabilización del modo con suavizado + debounce (Fases 2 y 10 del PLAN).

## ADR-005 — Catálogo filtrado y proyección vectorizada

- **Contexto:** el requisito es mostrar "las estrellas correctas donde apunto" en tiempo real.
- **Decisión:** catálogo filtrado a magnitud ≤ 6.5 (~9.000 estrellas, las visibles a simple vista); skyfield para la matriz de rotación del instante y las posiciones de los planetas; transformación y proyección con numpy vectorizado.
- **Alternativas:** astropy (correcto pero pesado para tiempo real) y el catálogo completo de ~118.000 estrellas (innecesario a 720p).
- **Consecuencias:** las posiciones son correctas para fecha/hora/lugar; la v1 usa azimut magnético sin corregir la declinación magnética (mejora futura sin cambiar la arquitectura).

**Actualización (2026-08-10, Fase 6):** el catálogo de trabajo es el **Yale Bright Star Catalog** (CDS V/50, `data/catalogo/bsc5.dat`, 8.404 estrellas con mag ≤ 6.5). HYG v3 no estaba disponible como descarga directa desde la red de desarrollo (el sitio oficial sirve páginas HTML); el BSC cubre el mismo rango que el filtro mag ≤ 6.5 del HYG. El cargador (`skyrender.catalogo`) acepta formatos por nombre (`formato="bsc"`, reservado `"hyg"`), así que migrar al HYG cuando sea accesible es trivial. El resto del ADR se mantiene: filtro mag ≤ 6.5, skyfield para el instante y planetas, proyección con numpy vectorizado.

## ADR-006 — Visualización con OpenCV en la v1

- **Contexto:** se necesita una ventana de escritorio para el feed + cielo.
- **Decisión:** OpenCV (`cv2.namedWindow`/`imshow`) para la v1. Un framework GUI (PySide6/Tkinter) solo si más adelante se quiere una UI rica.
- **Alternativas:** PySide6/Tkinter desde el inicio (mayor esfuerzo de UI sin valor para la v1).
- **Consecuencias:** sin dependencias GUI pesadas; la UI se limita a la ventana de vídeo.

## ADR-007 — Objetivo definitivo de 30 FPS a 720p

- **Contexto:** Dell Latitude 5320 con GPU integrada Iris Xe, sin GPU dedicada; además, la cámara web del hardware objetivo probablemente limita a 30 FPS.
- **Decisión:** **30 FPS a 720p como objetivo definitivo**. 60 FPS no tiene sentido si la cámara lo limita a 30.
- **Alternativas:** exigir 60 FPS desde el inicio (arriesgado y probablemente inútil si la cámara no lo soporta).
- **Consecuencias:** el PLAN y la Fase 10 incluyen benchmark y mitigaciones (resolución del cielo a 540p, caché de rotación, pre-render de la esfera celeste). Objetivo de diseño para la v1; el usuario inició la implementación sin objeciones a este objetivo, pero queda pendiente revalidarlo contra la cámara del hardware real durante la Fase 10.
