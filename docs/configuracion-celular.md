# Configuración del celular (brújula) — guía paso a paso

Objetivo: que el **Tecno Spark 10C** (Android 12) envíe rumbo e inclinación a la laptop.

Hay dos planes:
- **Plan A — WiFi + HTTPS**: el transporte por defecto. Requiere configurar un certificado auto-firmado una vez y un flag de Chrome.
- **Plan B — USB + adb reverse**: respaldo por cable. No requiere HTTPS.

Empieza por el plan A; usa el B si el A falla o si no hay WiFi disponible.

---

## 0. Verificar que la brújula del celular funciona

Antes de configurar nada, confirma que el magnetómetro responde:

1. En el celular abre una app de brújula (si no tienes, instala "Compass" de Google o cualquier app de brújula).
2. Mueve el celular en círculos en el aire (movimiento en "8") unos segundos para recalibrar el sensor.
3. Gira el celular y comprueba que la aguja/lectura cambia.
4. Confirma que apuntando al norte la app marca ~0°.

> [CAPTURA: pantalla de la app de brújula apuntando al norte]

Si la brújula no responde, este plan no funciona con este celular. Detente aquí.

---

## 1. Preparar la laptop

1. Abre PowerShell en `C:\Git\portal-al-cielo`.
2. Crea el entorno virtual: `python -m venv .venv`
3. Actívalo: `.\.venv\Scripts\Activate.ps1`
4. Instala las dependencias (detalle en la Fase 0 del PLAN).
5. Genera el certificado HTTPS **una sola vez**:
   - Ve a `tools/gen-cert` y sigue las instrucciones de su README.
   - En esencia: `openssl req -x509 -newkey rsa:2048 -nodes -keyout key.pem -out cert.pem -days 365`
   - Si no tienes openssl, usa el script Python alternativo incluido en esa carpeta.

> [CAPTURA: terminal con el certificado generado y los dos archivos key.pem / cert.pem]

---

## 2. Plan A — WiFi + HTTPS

### 2.1 Conectar laptop y celular a la misma red
Ambos deben estar en la misma red local (el mismo router/SSID). Anota la IP de la laptop: `ipconfig` en PowerShell → dirección IPv4 (tipo `192.168.x.x`).

### 2.2 Iniciar el servidor
Inicia la aplicación (o el servidor por separado, según el estado de implementación). Escucha en el puerto **8080** con HTTPS.

### 2.3 Preparar Chrome del celular
1. En Chrome abre: `chrome://flags/#unsafely-treat-insecure-origin-as-secure`
2. Escribe la URL segura del servidor: `https://192.168.x.x:8080` (usa la IP real de la laptop).
3. Activa el flag como **Enabled** y pulsa **Relaunch** (reabre Chrome).

> [CAPTURA: pantalla de chrome://flags con la IP marcada y el flag en Enabled]

### 2.4 Abrir la página y dar permiso del sensor
1. En Chrome abre `https://192.168.x.x:8080`
2. Acepta el aviso del certificado auto-firmado (Advanced → Proceed / Continuar).
3. La página pedirá permiso para el sensor de orientación; pulsa **Permitir**.
4. Deberías ver el **rumbo** y la **inclinación** en tiempo real.

> [CAPTURA: página web en el celular mostrando rumbo e inclinación]

Si la página no muestra el sensor: revisa que el flag quedó aplicado (paso 2.3) y que la brújula funciona (paso 0).

### 2.5 Calibrar
1. Coloca el celular **en la base de la laptop** (entre teclado y pantalla), pantalla hacia arriba y el borde superior apuntando hacia la pantalla de la laptop, es decir, **la misma orientación que la cámara**.
2. Gira el conjunto (laptop + celular) hasta que la lectura de la página (o de una app de brújula) marque ~0° (norte magnético).
3. Pulsa **"Calibrar"** en la página.
4. Desde ahora, el rumbo enviado a la laptop queda corregido con ese desfase.

> [CAPTURA: celular colocado en la base de la laptop]

---

## 3. Plan B — USB + adb reverse (respaldo)

Usa este plan si el A no funciona o no hay WiFi. El navegador trata `localhost` como origen seguro, así que **no hace falta HTTPS**.

### 3.1 Activar la Depuración USB en el celular
1. Ajustes → Acerca del teléfono → toca **"Número de compilación"** 7 veces (activa Modo desarrollador).
2. Ajustes → Opciones de desarrollador → activa **"Depuración USB"**.
3. Conecta el celular por USB y acepta el aviso "Permitir depuración USB".

### 3.2 Crear el túnel con adb
En la laptop (PowerShell):

```
adb reverse tcp:8080 tcp:8080
```

Verifica con `adb devices` que el dispositivo aparece como `device` (no `unauthorized`).

> [CAPTURA: terminal con `adb reverse` ejecutado y `adb devices` mostrando el dispositivo]

### 3.3 Abrir la página
En Chrome del celular abre `http://localhost:8080` y repite los pasos 2.4 y 2.5 (permiso del sensor y calibración).

---

## 4. Solución de problemas rápida

| Problema | Qué revisar |
|---|---|
| La página no pide permiso del sensor | Flag de Chrome aplicado y URL con `https://` en plan A, o `localhost` en plan B |
| El rumbo no cambia al girar | Recalibrar el magnetómetro con el movimiento en "8" (paso 0) |
| El rumbo está desplazado | Repetir la calibración (paso 2.5) |
| El WebSocket se desconecta | Misma WiFi, firewall de Windows permitiendo el puerto 8080 |
| `adb` no ve el celular | Revisar que la Depuración USB está activa y el aviso fue aceptado |

---

## Notas

- Los comandos exactos de inicio (openssl, adb) se documentan en `tools/gen-cert` y en las Fases 3 y 4 del PLAN.
- Esta guía se actualizará con **capturas reales** durante la implementación; los marcadores `[CAPTURA: ...]` indican dónde insertarlas.
- Los valores de rumbo se basan en el **norte magnético**; la corrección por declinación magnética es una mejora futura (ADR-005).
