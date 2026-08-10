"""Genera el certificado auto-firmado del servidor HTTPS (Plan A, ADR-001).

Genera `key.pem` y `cert.pem` en esta misma carpeta usando solo Python
(librería `cryptography`, sin depender de openssl en el PATH). Ambos archivos
están ignorados por git (ver .gitignore): son secretos/locales.

Uso:
    python tools/gen-cert/gen_cert.py
    python tools/gen-cert/gen_cert.py --ip 192.168.1.50   # SAN con IP
    python tools/gen-cert/gen_cert.py --force             # regenerar si existe
"""

import argparse
import ipaddress
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

DIR = Path(__file__).resolve().parent
KEY = DIR / "key.pem"
CERT = DIR / "cert.pem"
DAYS = 365


def generar(host_ip: str | None) -> None:
    if KEY.exists() and CERT.exists():
        raise FileExistsError(
            f"El certificado ya existe ({CERT.relative_to(DIR.parent.parent)}). "
            "Usa --force para regenerarlo."
        )

    clave = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    nombre = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "portal-al-cielo")])
    ahora = datetime.now(timezone.utc)

    builder = (
        x509.CertificateBuilder()
        .subject_name(nombre)
        .issuer_name(nombre)
        .public_key(clave.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(ahora - timedelta(minutes=5))
        .not_valid_after(ahora + timedelta(days=DAYS))
    )

    # subjectAltName: localhost siempre + IP de la laptop si se indica.
    sans = [x509.DNSName("localhost")]
    if host_ip:
        try:
            sans.append(x509.IPAddress(ipaddress.ip_address(host_ip)))
        except ValueError:
            print(f"Aviso: '{host_ip}' no es una IP válida; no se añade como SAN.")
    builder = builder.add_extension(
        x509.SubjectAlternativeName(sans), critical=False)

    certificado = builder.sign(clave, hashes.SHA256())

    KEY.write_bytes(clave.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    ))
    CERT.write_bytes(certificado.public_bytes(serialization.Encoding.PEM))
    print(f"[ok] Certificado auto-firmado generado:")
    print(f"     {KEY.relative_to(DIR.parent.parent)} (clave privada)")
    print(f"     {CERT.relative_to(DIR.parent.parent)} (certificado)")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--ip", default=None,
        help="IP de la laptop para incluirla como subjectAltName en el cert.",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Regenerar aunque el certificado ya exista.",
    )
    args = parser.parse_args(argv)

    if args.force:
        for f in (KEY, CERT):
            if f.exists():
                f.unlink()

    try:
        generar(args.ip)
    except FileExistsError as exc:
        print(exc, "o regenera con --force.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
