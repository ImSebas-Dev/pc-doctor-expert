"""Sesión, CSRF, control de acceso, límite de intentos, auditoría y cabeceras HTTP (OWASP Top 10)."""
import secrets
import time
from collections import defaultdict, deque
from functools import wraps

from flask import abort, current_app, g, request, session

from .db import uno, conexion

INACTIVIDAD, DURACION_MAX = 30 * 60, 8 * 3600
_SEGUROS = {"GET", "HEAD", "OPTIONS"}


class Limitador:
    """Ventana deslizante en memoria. El servicio corre con un solo proceso, por lo que el conteo es coherente."""

    def __init__(self, maximo: int, ventana: int):
        self.maximo, self.ventana, self._h = maximo, ventana, defaultdict(deque)

    def excedido(self, clave: str) -> bool:
        d, ahora = self._h[clave], time.monotonic()
        while d and ahora - d[0] > self.ventana:
            d.popleft()
        return len(d) >= self.maximo

    def registrar(self, clave: str) -> None:
        if len(self._h) > 5000:
            self._h.clear()
        self._h[clave].append(time.monotonic())

    def olvidar(self, clave: str) -> None:
        self._h.pop(clave, None)


fallos_por_ip = Limitador(20, 900)
fallos_por_correo = Limitador(5, 900)
registros_por_ip = Limitador(10, 3600)


def auditar(funcion: str, resultado: str, usuario_id: int | None = None) -> None:
    conexion().execute("INSERT INTO tx.auditoria_acceso(usuario_id,funcion,resultado) VALUES (%s,%s,%s)", (usuario_id, funcion, resultado))


def iniciar_sesion(usuario_id: int) -> str:
    """Crea una sesión nueva (evita la fijación de sesión) y devuelve su token CSRF."""
    session.clear()
    ahora = int(time.time())
    session.update(uid=usuario_id, ini=ahora, ult=ahora, csrf=secrets.token_urlsafe(32))
    return session["csrf"]


def antes_de_solicitud():
    g.usuario = None
    ahora = int(time.time())
    if "uid" in session:
        if ahora - session.get("ult", 0) > INACTIVIDAD or ahora - session.get("ini", 0) > DURACION_MAX:
            session.clear()
        else:
            session["ult"] = ahora
            g.usuario = uno("""SELECT u.id, u.nombre, u.correo, r.nombre AS rol FROM tx.usuario u JOIN tx.rol r ON r.id = u.rol_id
                               WHERE u.id = %s AND u.activo""", (session["uid"],))
            if g.usuario is None:
                session.clear()
    if request.path.startswith("/api/") and request.method not in _SEGUROS:
        if not request.is_json:
            abort(415)
        enviado, esperado = request.headers.get("X-CSRF-Token", ""), session.get("csrf", "")
        if not esperado or not secrets.compare_digest(enviado, esperado):
            abort(403)


def requiere_sesion(f):
    @wraps(f)
    def interior(*a, **k):
        if g.usuario is None:
            abort(401)
        return f(*a, **k)
    return interior


def requiere_admin(f):
    @wraps(f)
    @requiere_sesion
    def interior(*a, **k):
        if g.usuario["rol"] != "administrador":
            auditar(f"acceso_admin {request.path}"[:60], "denegado", g.usuario["id"])
            abort(403)
        return f(*a, **k)
    return interior


def cabeceras(r):
    r.headers["Content-Security-Policy"] = ("default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; "
                                            "connect-src 'self'; manifest-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["Referrer-Policy"] = "no-referrer"
    r.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
    r.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    r.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    r.headers["Cache-Control"] = "no-store" if request.path.startswith("/api/") else "no-cache"
    if current_app.config["PRODUCCION"]:
        r.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return r
