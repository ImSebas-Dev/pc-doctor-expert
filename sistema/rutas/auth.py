"""Cuentas: sesión, registro, inicio y cierre de sesión, perfil (RF-01)."""
import secrets

import psycopg.errors
from flask import Blueprint, abort, g, jsonify, request, session

from .. import claves
from ..db import conexion, uno
from ..seguridad import (auditar, fallos_por_correo, fallos_por_ip, iniciar_sesion, registros_por_ip, requiere_sesion)
from ..validacion import CORREO, ErrorValidacion, cadena, cuerpo

bp = Blueprint("auth", __name__, url_prefix="/api")


def _publico(u):
    return {"nombre": u["nombre"], "correo": u["correo"], "rol": u["rol"]}


@bp.get("/sesion")
def sesion():
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return jsonify(usuario=_publico(g.usuario) if g.usuario else None, csrf=session["csrf"])


@bp.post("/registro")
def registro():
    if registros_por_ip.excedido(request.remote_addr):
        abort(429)
    registros_por_ip.registrar(request.remote_addr)
    d = cuerpo()
    nombre = cadena(d, "nombre", "Nombre", 2, 80)
    correo = cadena(d, "correo", "Correo", 5, 120, CORREO).lower()
    clave = cadena(d, "clave", "Contraseña", 1, 1000, recortar=False)
    if (motivo := claves.error_de_politica(clave, correo)):
        raise ErrorValidacion(motivo, "clave")
    try:
        with conexion().transaction():
            fila = uno("INSERT INTO tx.usuario(nombre,correo,clave_hash,rol_id) VALUES (%s,%s,%s,(SELECT id FROM tx.rol WHERE nombre='usuario')) RETURNING id",
                       (nombre, correo, claves.crear_hash(clave)))
    except psycopg.errors.UniqueViolation:
        raise ErrorValidacion("Ya existe una cuenta con ese correo. Inicia sesión o usa otro correo.", "correo")
    csrf = iniciar_sesion(fila["id"])
    return jsonify(usuario={"nombre": nombre, "correo": correo, "rol": "usuario"}, csrf=csrf), 201


@bp.post("/login")
def login():
    d = cuerpo()
    correo = cadena(d, "correo", "Correo", 1, 120).lower()
    clave = cadena(d, "clave", "Contraseña", 1, 1000, recortar=False)
    if fallos_por_ip.excedido(request.remote_addr) or fallos_por_correo.excedido(correo):
        abort(429)
    u = uno("SELECT u.id, u.nombre, u.correo, u.clave_hash, u.activo, r.nombre AS rol FROM tx.usuario u JOIN tx.rol r ON r.id=u.rol_id WHERE u.correo=%s", (correo,))
    correcto = claves.verificar(clave, u["clave_hash"] if u else claves.HASH_FALSO)
    if not (u and u["activo"] and correcto):
        fallos_por_ip.registrar(request.remote_addr)
        fallos_por_correo.registrar(correo)
        auditar("login", "denegado", u["id"] if u else None)
        return jsonify(error="Correo o contraseña incorrectos."), 401
    fallos_por_correo.olvidar(correo)
    auditar("login", "permitido", u["id"])
    return jsonify(usuario=_publico(u), csrf=iniciar_sesion(u["id"]))


@bp.post("/logout")
@requiere_sesion
def logout():
    session.clear()
    session["csrf"] = secrets.token_urlsafe(32)
    return jsonify(csrf=session["csrf"])


@bp.put("/perfil")
@requiere_sesion
def perfil():
    d = cuerpo()
    nombre = cadena(d, "nombre", "Nombre", 2, 80)
    if d.get("clave_nueva"):
        actual = cadena(d, "clave_actual", "Contraseña actual", 1, 1000, recortar=False)
        nueva = cadena(d, "clave_nueva", "Contraseña nueva", 1, 1000, recortar=False)
        fila = uno("SELECT clave_hash FROM tx.usuario WHERE id=%s", (g.usuario["id"],))
        if not claves.verificar(actual, fila["clave_hash"]):
            raise ErrorValidacion("La contraseña actual no es correcta.", "clave_actual")
        if (motivo := claves.error_de_politica(nueva, g.usuario["correo"])):
            raise ErrorValidacion(motivo, "clave_nueva")
        conexion().execute("UPDATE tx.usuario SET nombre=%s, clave_hash=%s WHERE id=%s", (nombre, claves.crear_hash(nueva), g.usuario["id"]))
    else:
        conexion().execute("UPDATE tx.usuario SET nombre=%s WHERE id=%s", (nombre, g.usuario["id"]))
    return jsonify(usuario={**_publico(g.usuario), "nombre": nombre})
