# ARQUITECTURA — Portal al Cielo

## 1. Visión general

Aplicación de escritorio (Windows) que en tiempo real:

1. Captura la cámara web.
2. Detecta el marco formado por dos manos (MediaPipe).
3. Calcula el cielo real para la dirección de la cámara, usando la brújula del celular como fuente de rumbo/inclinación.
4. Incrusta el cielo dentro del marco. El resto del feed permanece normal.

Objetivo de rendimiento: **30 FPS a 720p** en Dell Latitude 5320 (Iris Xe, sin GPU dedicada). Ver ADR-007.

## 2. Flujo de datos

```
Celular (brújula)                          Laptop (aplicación)
[DeviceOrientation API] --WebSocket/UDP--> src/server (estado {rumbo, inclinacion, roll})
                                                   |
cámara --> src/handtracking (cuadrilátero)         v
            |                              src/skyrender (imagen del cielo)
            v                                         |
            +----------> src/compositor <-------------+
                              |
                              v
                    Ventana de escritorio
```

Estructura de ejecución:

- **Hilo del servidor**: atiende el WebSocket del celular y actualiza un estado compartido en memoria `{rumbo, inclinacion, roll, ts}`. Es la única fuente de verdad de orientación.
- **Bucle principal**: captura de cámara → detección de manos → render del cielo → composición → visualización. (Opcional: un tercer hilo de captura para desacoplar el feed.)

## 3. Módulos y responsabilidades

### `src/app`
Ventana de escritorio y captura de cámara con OpenCV. En la v1 la visualización se hace con `cv2.namedWindow`/`imshow` (sin framework GUI pesado; ver ADR-006). Resolución objetivo 720p a 30 FPS.

### `src/handtracking`
Detección de manos con **MediaPipe Hands** (bindings oficiales de Python). Extrae los landmarks relevantes por mano (tip de pulgar = landmark 4, tip de índice = 8, tip de medio = 12) y la lateralidad (mano izquierda/derecha) para asignar correctamente las esquinas del rectángulo. Construye el cuadrilátero con 4 puntos.

Incluye:

- **Suavizado** de los landmarks (filtro exponencial o one-euro) para evitar el temblor de la detección.
- **Validación geométrica** del cuadrilátero (área mínima, orden de vértices, no degeneración). Crítico en el modo "V", donde los dos landmarks de una misma mano quedan muy próximos entre sí (ver ADR-004).
- **Selección de modo** según el par de dedos levantados.

### `src/skyrender`
Astrometría y render del cielo. Es el módulo donde se garantiza que las estrellas sean **correctas para el punto de mira**:

1. Carga el catálogo filtrado (magnitud ≤ 6.5, unas 9.000 estrellas) preconvertido a vectores unitarios en coordenadas ecuatoriales.
2. Con **skyfield** calcula, para el instante (fecha/hora del sistema + ubicación geográfica configurada), la **matriz de rotación ecuatorial → horizontal** y las posiciones aparentes de los planetas (efemérides `de421.bsp`).
3. Construye la **matriz de vista de cámara** a partir de `{rumbo, inclinacion, roll}` y un FOV configurable.
4. Proyecta con **numpy vectorizado** (una sola transformación de matrices, no una llamada de skyfield por estrella) y dibuja las estrellas con tamaño y brillo según magnitud, las constelaciones (líneas) y las etiquetas según el modo activo.

**Por qué así:** iterar ~9.000 estrellas con skyfield en cada frame es demasiado lento para una Iris Xe; la proyección vectorizada con numpy es lo que permite 30 FPS.

#### Estrategia de precomputación y caché

Responde a la pregunta "¿no se puede calcular el cielo una vez y reutilizarlo?". Sí, en tres niveles, y así se evita recalcular la astronomía en cada frame:

1. **Catálogo precargado (una sola vez, al iniciar):** las ~9.000 estrellas se convierten a vectores unitarios y quedan en memoria. Las estrellas no se mueven en el cielo (sus coordenadas ecuatoriales son fijas a escala humana), así que esto **no se recalcula nunca**. Es "descargar el render" en su sentido válido.
2. **Caché de rotación (recalcular cada 1–2 minutos):** la matriz ecuatorial → horizontal depende de la hora; el cielo rota ~1° cada 4 minutos. La matriz se cachea y solo se recalcula cuando el reloj avanza lo suficiente. No es recalcular estrellas, es girar el marco de referencia.
3. **Por frame solo se proyecta (1–2 ms):** la matriz de vista de cámara cambia cada vez que se mueve la brújula/cámara, pero aplicarla a los 9.000 vectores con numpy es una multiplicación de matrices trivial. No es "recalcular el cielo", es reproyectarlo.

Optimización adicional (Fase 10): **pre-render de la esfera celeste completa** como textura equirectangular, rotada en cada frame según el tiempo sidéreo, en lugar de proyectar estrella por estrella. La textura se regenera solo cuando es necesario (movimiento de los planetas), no por frame.

Matiz importante sobre el "render del día": fijar el cielo durante un día completo es perfectamente válido para las **estrellas**. Su desplazamiento aparente es despreciable a corto plazo (precesión ~0,014° por año; movimiento propio de arcosegundos por año): una estrella seguirá estando "casi exactamente ahí" esta noche, mañana y dentro de semanas. Lo único que se mueve de forma perceptible entre días son los **planetas** (y sobre todo la Luna), así que la v1 puede elegir: (a) aceptar esa pequeña imprecisión, o (b) recalcular solo los planetas una vez al día (cuesta centésimas de segundo con skyfield). Además no hay nada que "descargar" por día: el catálogo es local y pequeño (~1–2 MB, se descarga una sola vez); el render del día se genera localmente y se reutiliza. La parte astronómica del render no es el costo real; el costo es dibujar los puntos, y eso lo cubre el pre-render de la esfera celeste (Fase 10).

### `src/compositor`
Recibe el frame de cámara y la imagen del cielo renderizada. Calcula la **homografía** desde las 4 esquinas del marco y aplica `warpPerspective` para incrustar el cielo en el cuadrilátero. Mezcla con el feed; el resto de la imagen queda igual.

### `src/server`
Servidor web con **aiohttp** que:

- Sirve la página estática del celular en `/`.
- Expone un **WebSocket** en `/ws` que recibe `{rumbo, inclinacion, roll, ts}` a 30–60 Hz.
- Aplica la **corrección de calibración** (offset de rumbo).
- Mantiene el último estado en memoria, accesible para `skyrender`.
- En el plan A corre con **HTTPS** (certificado auto-firmado); en el plan B corre en HTTP local vía `adb reverse`.

### `data/catalogo`
Catálogo de estrellas (HYG v3 o Hipparcos) filtrado a magnitud ≤ 6.5. El origen y el script de filtrado se detallan en la Fase 6 del PLAN.

### `tools/gen-cert`
Script que genera una sola vez el certificado auto-firmado para el plan A (vía `openssl` o Python puro).

### `tests`
Pruebas unitarias por módulo: transformación de coordenadas, validación del cuadrilátero, corrección de calibración, protocolo WebSocket.

## 4. Protocolo celular → laptop

Mensaje JSON por WebSocket:

```json
{"tipo": "orientacion", "rumbo": 212.3, "inclinacion": 8.5, "roll": 0.0, "ts": 1720000000.123}
```

- `rumbo`: 0–360 grados (azimut magnético).
- `inclinacion`: -90 a +90 (0 = horizontal).
- `roll`: giro del celular (en la v1 se recibe; su uso en la orientación del cielo es opcional).
- `ts`: marca de tiempo para descartar datos obsoletos.

Frecuencia de envío: 30–60 Hz. UDP queda anotado como plan B de transporte si WebSocket no fuera viable.

## 5. Calibración

1. El usuario coloca el celular en la base de la laptop (entre teclado y pantalla), con la misma orientación que la cámara.
2. Orienta el conjunto hasta que la lectura del celular marque **norte magnético** (~0), usando la lectura de la página o una app de brújula.
3. Pulsa **"Calibrar"** en la página. El servidor guarda el offset y desde entonces `rumbo_efectivo = (rumbo_celular − offset) mod 360`.

Esta definición de calibración queda **pendiente de validar** con el usuario (ver mensaje de cierre del diseño).

## 6. Riesgos y límites conocidos

- **Iris Xe sin GPU dedicada**: el render del cielo debe mantenerse vectorizado. Si no se llega a 30 FPS, mitigación prevista: reducir la resolución de la imagen del cielo a 540p (Fase 10).
- **Modo "V" (índice + medio)**: los dos landmarks de una misma mano quedan muy próximos → cuadrilátero casi degenerado. Se mitiga con suavizado y validación geométrica.
- **Sin magnetómetro en la laptop**: la fuente de rumbo es obligatoriamente externa (el celular). Si el celular falla, no hay modo de fallback automático.
- **Norte magnético ≠ norte verdadero**: en la v1 se usa el azimut magnético tal cual. La declinación magnética del lugar se puede incorporar después sin cambiar la arquitectura (solo es un offset en `skyrender`).

## 7. Documentos relacionados

- `DECISIONES.md` — ADR-001 a ADR-007.
- `PLAN.md` — fases de implementación.
- `docs/configuracion-celular.md` — guía de configuración del celular.
