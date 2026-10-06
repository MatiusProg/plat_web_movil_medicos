"""Característica general 6 — Cómo se guarda cifrada una copia automática.

    contenido JSON  →  gzip  →  Fernet  →  columna ``backup_files.content``

**Por qué se cifra aunque la tabla tenga RLS.** RLS protege de la aplicación
—de un inquilino que pide lo de otro—, no de quien tiene la base: un volcado
de Supabase, una réplica, una consulta como ``postgres``. Esa copia lleva en
claro todo lo que el sistema protege, y sin cifrar la tabla de respaldos sería
el lugar más rentable para atacar, que es justo lo que ``services`` quería
evitar al no guardar las copias manuales. La clave vive fuera de la base, en
las variables de Railway: con la base sola no alcanza.

**Fernet y no AES a mano.** Fernet es AES con un HMAC encima: además de
ocultar, detecta un contenido alterado o cortado, y no deja ninguna decisión
criptográfica —modo, relleno, vector— en manos de quien lo usa.

**gzip antes de cifrar**, porque después no comprime nada: lo cifrado parece
azar. Un JSON de respaldo se reduce a menos de una décima parte.
"""

import base64
import gzip
import hashlib

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings


class VaultError(Exception):
    """El contenido no se pudo descifrar: otra clave, o está dañado."""


def _derivada() -> str:
    """La clave que sale de SECRET_KEY, con un prefijo propio para que no sea
    la misma que usa Django para otra cosa."""
    resumen = hashlib.sha256(
        b"plataforma-medica:backups:" + settings.SECRET_KEY.encode("utf-8"),
    ).digest()
    return base64.urlsafe_b64encode(resumen).decode("ascii")


def _fernet() -> MultiFernet:
    """Cifra con la primera clave y descifra con cualquiera.

    Con ``BACKUP_ENCRYPTION_KEY`` definida se cifra con ella, pero se sigue
    pudiendo leer lo que se cifró antes con la derivada de SECRET_KEY. Pasó
    en producción el 06/10/26: el primer despliegue respaldó antes de que se
    cargara la clave, y sin esto esas copias habrían quedado ilegibles. Es
    también cómo se rota la clave: la nueva primero, la vieja después.
    """
    claves = []
    propia = getattr(settings, "BACKUP_ENCRYPTION_KEY", "") or ""
    if propia:
        claves.append(Fernet(propia))
    claves.append(Fernet(_derivada()))
    return MultiFernet(claves)


def seal(contenido: bytes) -> bytes:
    """Comprime y cifra."""
    return _fernet().encrypt(gzip.compress(contenido, compresslevel=6))


def open_sealed(sellado: bytes) -> bytes:
    """Descifra y descomprime. ``VaultError`` si no se puede."""
    try:
        return gzip.decompress(_fernet().decrypt(bytes(sellado)))
    except (InvalidToken, OSError) as error:
        raise VaultError(
            "La copia guardada no se pudo descifrar: la clave de cifrado "
            "cambió o el contenido está dañado.",
        ) from error
