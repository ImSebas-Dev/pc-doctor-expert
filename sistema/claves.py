"""Hash y política de contraseñas (solo biblioteca estándar: scrypt)."""
import base64
import hashlib
import hmac
import os
import secrets

_N, _R, _P = 2**14, 8, 1
MIN_LARGO, MAX_LARGO = 10, 128
_COMUNES = {"1234567890", "contraseña1", "contrasena1", "password123", "qwertyuiop", "0123456789", "admin12345", "pcdoctor123"}


def _derivar(clave: str, sal: bytes) -> bytes:
    return hashlib.scrypt(clave.encode(), salt=sal, n=_N, r=_R, p=_P, dklen=32)


def crear_hash(clave: str) -> str:
    sal = os.urandom(16)
    return "scrypt$" + base64.b64encode(sal).decode() + "$" + base64.b64encode(_derivar(clave, sal)).decode()


def verificar(clave: str, almacenado: str) -> bool:
    try:
        _, sal, esperado = almacenado.split("$")
        return hmac.compare_digest(_derivar(clave, base64.b64decode(sal)), base64.b64decode(esperado))
    except ValueError:
        return False


HASH_FALSO = crear_hash(secrets.token_urlsafe(12))  # se verifica contra él cuando el correo no existe (tiempo constante)


def error_de_politica(clave: str, correo: str = "") -> str | None:
    """Devuelve el motivo por el que la clave no es aceptable, o None si lo es."""
    if not MIN_LARGO <= len(clave) <= MAX_LARGO:
        return f"La contraseña debe tener entre {MIN_LARGO} y {MAX_LARGO} caracteres."
    if clave.lower() in _COMUNES or clave.lower() == correo.lower() or len(set(clave)) < 4:
        return "Esa contraseña es demasiado común o predecible. Elige otra."
    return None
