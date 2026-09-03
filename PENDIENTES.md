# PENDIENTES — Cambios propuestos

Registro de cambios y mejoras identificados en la **revisión crítica del
proyecto (2026-08-11)**. Nada de esto está aplicado todavía; cada entrada
indica dónde tocar (`archivo:línea`), qué problema resuelve y cómo
verificarlo. La suite al momento de la revisión: **125/125 tests en verde**.

Orden de prioridad: **1** bugs a corregir (por severidad) → **2** decisiones
pendientes → **3** mejoras opcionales → **4** cosas que no conviene tocar.

---

## 1. Bugs a corregir

### 1.1 El servidor falla en silencio y la app no lo dice — **ALTA**

- **Ubicación:** `src/app/main.py:82-85`
- **Problema:** `_arrancar_servidor` hace `except Exception: pass`. Si el
  puerto 8080 está ocupado (otra instancia, otro servicio) o el certificado
  es ilegible, el `OSError` se traga: el launcher imprime las instrucciones
  como si todo fuera bien y la demo corre **sin brújula para siempre**. El
  hilo `CompassReader` (`demo_compositor.py`) también se traga cada error de
  conexión. El usuario solo se entera pulsando `i` y viendo "sin lectura".
- **Cambio propuesto:** capturar la excepción en `_arrancar_servidor` y
  dejarla accesible (p. ej. un `threading.Event` que guarde el error, o
  imprimir el traceback); que `CompassReader` avise una vez si nunca logra
  conectar.
- **Verificación:** test de integración que intente `iniciar_servidor` en un
  puerto ya ocupado y confirme que el launcher lo reporta.

### 1.2 Acrux y Alpha Centauri sin nombre propio — **ALTA**

- **Ubicación:** `src/skyrender/render.py:143-147` (parsing Bayer);
  `src/skyrender/catalogo.py:110-120` (`buscar_designacion`).
- **Problema:** el parsing `tokens[0].lstrip("0123456789 ")` solo quita
  dígitos al **inicio** del token, pero el BSC guarda los componentes como
  `Alp1Cru` y `Alp1Cen`. Resultado: **2 de las 31 claves de
  `NOMBRES_PROPIOS` nunca se asignan** (`Alp Cen` → Rigil Kentaurus y
  `Alp Cru` → Acrux). Desde la latitud del usuario (~9.66°N) ambas son
  visibles según la estación, y quedan sin etiqueta ni en la lista de la
  tecla `o`. Además, `buscar_designacion` devuelve el **primer** match, así
  que `Alp2Cru` resuelve a la componente equivocada (visualmente
  despreciable por estar a minutos de arco, pero es un mapeo incorrecto).
- **Cambio propuesto:** eliminar también los dígitos internos del token
  Bayer (p. ej. `re.sub(r"\d", "", tokens[0])` antes de construir la clave)
  para que `Alp1Cru` → `Alp Cru`.
- **Verificación:** test de regresión que garantice que **todas** las claves
  de `NOMBRES_PROPIOS` se asignan a alguna estrella del catálogo (hoy hay 2
  huérfanas y ningún test las cubre). Tras el arreglo, Acrux y Rigil
  Kentaurus deben aparecer etiquetadas y en `objetos_visibles`.

### 1.3 Los planetas ignoran `--lat/--lon` en la demo — **MEDIA**

- **Ubicación:** `src/compositor/demo_compositor.py` (construcción del
  renderer) y `src/skyrender/render.py:151-156` (`_topos`).
- **Problema:** el renderer se construye sin `ubicacion` (carga
  `data/ubicacion.json`) y luego se hace `renderer.ubicacion = ubicacion`.
  Pero `self._topos` (el observador de las efemérides de los planetas) se
  construyó en `__init__` con la ubicación anterior. Si se corre
  `--lat X --lon Y` distintos de la guardada, las **estrellas** usan la
  nueva posición y los **planetas/Luna** la vieja: desalineación de hasta
  grados según la diferencia. En uso normal (una sola ubicación) pasa
  desapercibido.
- **Cambio propuesto:** pasar `ubicacion=ubicacion` al construir
  `SkyRenderer`, o recrear `_topos` cuando cambia `renderer.ubicacion`.

### 1.4 "Calibrar al norte" se habilita antes de la primera lectura — **MEDIA**

- **Ubicación:** `src/server/static/celular.html:29` y `:107-109`; `:66`.
- **Problema:** el botón `Calibrar` se habilita en cuanto se activa el
  sensor (`btnCal.disabled = false`), no cuando llega la **primera** lectura
  del magnetómetro. `celular.html:66` convierte `e.alpha === null` en 0, así
  que si el usuario calibra antes de que el sensor entregue datos, calibra a
  rumbo 0 creyendo que calibró. Es un caso real: la DeviceOrientation API a
  veces tarda en disparar.
- **Cambio propuesto:** habilitar el botón solo al recibir la primera lectura
  válida (`e.alpha !== null`).

### 1.5 El registro (logging) es mudo en el launcher `portal` — **BAJA**

- **Ubicación:** `src/server/web.py:24` (`logging.getLogger("portal.server")`);
  `src/app/main.py`.
- **Problema:** el middleware de peticiones añadido en la Fase 3 loguea a
  `portal.server`, pero `portal` no llama a `logging.basicConfig` (solo
  `python -m server` lo hace). En la ruta normal de la app no escribe nada.
- **Cambio propuesto:** añadir `logging.basicConfig` en `main.py` (nivel
  INFO), o documentar que el middleware queda mudo en `portal`.

### 1.6 Consola de Windows con acentos y rayas — **BAJA (cosmético)**

- **Ubicación:** varios `print` y `--help` (p. ej. `demo_compositor.py`,
  `main.py`) usan "—", "brújula", "estética".
- **Problema:** `sys.stdout.encoding` es `cp1252` y, por tubería, el em dash
  sale como `�`; en consola cp850 (común en es-ES) o con redirección a
  archivo puede no ser representable e incluso lanzar `UnicodeEncodeError`.
- **Cambio propuesto:** en los mensajes que puedan ir a logs/archivo, usar
  ASCII (p. ej. `-` en vez de `—`) o configurar la salida a UTF-8.

### 1.7 Doc: la Fase 4 (Plan B) sigue marcada "Pendiente" — **BAJA**

- **Ubicación:** `PROGRESO.md:340`.
- **Problema:** la tabla marca `| 4 | Plan B (USB + adb reverse) | Pendiente |`
  cuando el Plan B ya está implementado y documentado (`--no-tls`,
  `docs/configuracion-celular.md`).
- **Cambio propuesto:** actualizar a "Hecho (implementado)" o la redacción
  equivalente; corroborar con una prueba real del flujo adb antes de poner
  "validado".

---

## 2. Decisiones pendientes (no son bugs; decidir a conciencia)

- **Espejo ↔ cielo sin espejar.** La cámara se muestra espejada (modo
  selfie) pero el cielo se renderiza sin voltear (nombres legibles). Medido:
  ~37° de desplazamiento en el borde de un FOV de 60° entre lo que el usuario
  percibe y el anclaje del cielo al fondo de la escena. El movimiento lateral
  es consistente; la correspondencia estática "qué estrella queda detrás de
  qué edificio" es la invertida. Probar `--no-espejo` y decidir si el anclaje
  espacial importa. Documentado en `README.md:61-65`.
- **Estética "noche profunda" bajo el horizonte.** `src/skyrender/estetica.py:94`
  pinta el degradado azul en toda la imagen, incluso mirando al suelo (sin
  estrellas). Aceptable como estética, pero es una decisión visual a tener
  presente.
- **`order_quad_points` con el marco rotado.** `src/handtracking/quadrilateral.py:43-44`
  usa el método de imutils que asume un rectángulo casi alineado con la
  imagen; con el marco de manos fuertemente rotado el orden TL/TR/BR/BL puede
  equivocarse y el cuadrilátero se "retuerce". Tolerable en uso real (las
  manos suelen mantenerse horizontales), pero es la pieza menos robusta de la
  geometría.

---

## 3. Mejoras opcionales

- **Sugerir/detectar la IP en el certificado.** `tools/gen-cert/gen_cert.py`
  solo mete `localhost` en el SAN por defecto, así que el celular siempre
  salta la advertencia del certificado por IP. Documentar
  `python tools/gen-cert/gen_cert.py --ip <IP>` en el flujo de arranque, o
  detectar la IP automáticamente.
- **Soak de ~10 minutos con el marco activo.** El benchmark real midió
  30 FPS sin manos; la estabilidad con el pipeline completo y el marco
  formado sigue sin validarse (ya apuntado en `PROGRESO.md` como pendiente
  del ADR-007).
- **Cachear `mags`.** `src/skyrender/render.py:374` reconstruye el array de
  magnitudes por frame desde ~8.400 estrellas; es trivial precalcularlo en
  `__init__`. No es cuello de botella, solo pulcritud.
- **Test del caso "puerto ocupado"** que cierre el hueco de 1.1 (no existe).

---

## 4. No tocar (riesgo de romper algo que funciona)

- **La astrometría propia (`src/skyrender/astro.py`).** Es lo que permite los
  30 FPS con ~8.400 estrellas; skyfield queda solo como referencia de tests.
  "Simplificarla" sería volver a la iteración por estrella.
- **El modo `ventana` como predeterminado.** Más rápido (sin
  `warpPerspective`) y físicamente correcto. Conservar `completo` para
  comparar/diagnóstico.
- **El `--no-tls` / Plan B.** Es el respaldo cuando falla el WiFi/HTTPS o el
  flag de Chrome molesta.
- **El fix de reloj de `fresh`** en la brújula (reloj del servidor, no del
  cliente). Volver al `ts` del cliente reaparecería el bug de relojes
  desincronizados.
- **La separación estética/astronomía (`estetica.py` como post-proceso).** Es
  lo que permite validar la astronomía independientemente de la estética.
- **La lista de objetos y el apuntado por teclado (tecla `o`).** Es la única
  forma de apuntar sin celular y la herramienta con la que se validó la
  astronomía.

---

## Estado de aplicación (2026-08-11)

Los bugs de la sección 1 quedaron **aplicados** tras la revisión. La suite
pasó de **125/125** a **137/137 tests en verde** (12 tests de regresión
nuevos). La sección 2 (decisiones) y la 3 (mejoras) siguen abiertas.

| Bug | Estado | Dónde |
|---|---|---|
| 1.1 Servidor falla en silencio | Aplicado | `src/app/main.py` (`_arrancar_servidor` reporta el error; `main` aborta con código 1) y `src/compositor/demo_compositor.py` (`CompassReader` avisa una vez si nunca conecta) |
| 1.2 Acrux y Alpha Centauri sin nombre propio | Aplicado | `src/skyrender/render.py` (parsing Bayer que separa la constelación de 3 letras de las componentes) |
| 1.3 Planetas ignoran `--lat/--lon` | Aplicado | `src/compositor/demo_compositor.py` (la `ubicacion` se pasa al construir `SkyRenderer`) |
| 1.4 "Calibrar" se habilita antes de la primera lectura | Aplicado | `src/server/static/celular.html` (solo la primera lectura válida habilita el botón; `alpha` nulo ya no se falsifica a 0) |
| 1.5 Logging mudo en el launcher `portal` | Aplicado | `src/app/main.py` (`logging.basicConfig` en `main`) |
| 1.6 Consola de Windows con acentos y rayas | Aplicado | `src/app/main.py` y `src/compositor/demo_compositor.py` (em dash a ASCII en stdout/help + `reconfigure(errors="replace")`) |
| 1.7 Fase 4 (Plan B) "Pendiente" | Aplicado | `PROGRESO.md` (tabla → "Hecho (implementado)"; sin afirmar "validado" hasta probar el flujo adb) |

