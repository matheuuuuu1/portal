# gen-cert — certificado HTTPS auto-firmado (Plan A)

Genera una sola vez los archivos `key.pem` y `cert.pem` que usa el servidor de
la brújula para correr con HTTPS (ADR-001, Plan A). **No se versionan en git.**

## Uso

```
python tools/gen-cert/gen_cert.py
```

Opcional, para que el certificado incluya la IP de la laptop como
subjectAltName (evita el aviso en Chrome del celular):

```
python tools/gen-cert/gen_cert.py --ip 192.168.x.x
```

Para regenerar (por ejemplo, si cambia la IP de la red):

```
python tools/gen-cert/gen_cert.py --force --ip 192.168.x.x
```

## Requisito

Python con la librería `cryptography` (incluida en `requirements.txt`).
No depende de `openssl` en el PATH.

## Qué genera

- `key.pem` — clave privada (secreto, no compartir).
- `cert.pem` — certificado auto-firmado, válido 365 días.

El servidor se inicia con:

```
python -m server --tls
```
