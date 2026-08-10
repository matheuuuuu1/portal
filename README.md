# Portal al Cielo

Aplicación de escritorio para **Windows** que convierte la cámara web de la laptop en un portal al cielo: cuando el usuario forma un **marco de ventana** con las manos (dos manos, dos dedos por mano), dentro de ese marco se muestra el **cielo estrellado real** correspondiente a la dirección hacia donde apunta la cámara en ese instante. El resto de la imagen de la cámara permanece normal. Todo en tiempo real.

## Cómo funciona en una frase

Tu celular Android hace de brújula (magnetómetro) y envía rumbo e inclinación a la laptop por WiFi (HTTPS) o por cable USB (adb reverse). La laptop calcula con esos datos qué estrellas hay en esa porción de cielo y las dibuja dentro del marco que forman tus manos.

## Dos modos de gesto

El marco lo forman siempre **dos manos**, cada una aporta **dos dedos** (4 esquinas del rectángulo). El par de dedos elegido cambia el modo:

- **Pulgar + índice** de cada mano (forma de L): se ven constelaciones y planetas, **sin nombres**.
- **Índice + dedo medio** de cada mano (forma de V): las mismas constelaciones y planetas, pero los **más importantes muestran su nombre** al lado.

> Nota: esta interpretación del gesto está pendiente de validación final (ver mensaje de cierre del diseño).

## Requisitos

- Windows 10/11.
- Laptop con cámara web. Objetivo validado: Dell Latitude 5320 (Intel 11.ª gen, GPU integrada Iris Xe).
- Python 3.10 o superior.
- Celular Android con brújula/e-compass. Validado: Tecno Spark 10C (Android 12, HIOS 8.6).
- Red WiFi local (plan A) o cable USB (plan B) para la comunicación de la brújula.

## Cómo empezar (resumen)

1. Clonar el proyecto y crear el entorno virtual de Python.
2. Instalar las dependencias.
3. Generar el certificado HTTPS auto-firmado (una sola vez): `tools/gen-cert`.
4. Iniciar la aplicación.
5. Configurar el celular siguiendo `docs/configuracion-celular.md`, abrir la página y calibrar.

## Estructura del proyecto

| Ruta | Responsabilidad |
|---|---|
| `src/app` | Ventana de escritorio + captura de cámara |
| `src/handtracking` | Detección de manos con MediaPipe → cuadrilátero del marco |
| `src/skyrender` | Astrometría + catálogo → cielo de esa dirección |
| `src/compositor` | Mezcla del feed de cámara con el cielo dentro del marco |
| `src/server` | Servidor web/WebSocket para la brújula del celular |
| `data/catalogo` | Catálogo de estrellas (descargado y filtrado) |
| `tools/gen-cert` | Generación del certificado HTTPS auto-firmado |
| `docs` | Guías de configuración |
| `tests` | Pruebas unitarias por módulo |

## Documentación

- `ARQUITECTURA.md` — estructura, módulos, flujo de datos y decisiones de diseño.
- `PLAN.md` — fases de implementación con criterio de "hecho" para cada una.
- `DECISIONES.md` — registro de decisiones de diseño (ADR).
- `docs/configuracion-celular.md` — configuración de la brújula del celular (plan A WiFi y plan B USB).

## Estado

Diseño inicial completado. La implementación está en curso según `PLAN.md`;
el seguimiento fase por fase está en `PROGRESO.md`.
