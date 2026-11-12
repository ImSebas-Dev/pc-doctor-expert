"""Punto de entrada: crea la aplicación Flask de PC Doctor Expert."""
import logging
import os
import secrets

from flask import Flask, jsonify, send_from_directory
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

from sistema import db, instalador, seguridad
from sistema.rutas import admin, auth, diagnostico, equipos
from sistema.validacion import ErrorValidacion

MENSAJES = {400: "Solicitud no válida.", 401: "Debes iniciar sesión.", 403: "No tienes permiso para esta acción.", 404: "No se encontró lo solicitado.",
            405: "Método no permitido.", 413: "La solicitud es demasiado grande.", 415: "Formato no admitido.",
            429: "Demasiados intentos. Espera unos minutos e inténtalo de nuevo."}


def crear_app(config: dict | None = None) -> Flask:
    app = Flask(__name__, static_folder="static", static_url_path="")
    produccion = os.environ.get("PCDOCTOR_ENV") == "production"
    app.config.update(
        PRODUCCION=produccion, DATABASE_URL=os.environ.get("DATABASE_URL"), MAX_CONTENT_LENGTH=32 * 1024,
        SECRET_KEY=os.environ.get("SECRET_KEY") or (None if produccion else secrets.token_hex(32)),
        SESSION_COOKIE_NAME="__Host-sesion" if produccion else "sesion", SESSION_COOKIE_SECURE=produccion,
        SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax", JSON_SORT_KEYS=False,
    )
    app.config.update(config or {})
    if not app.config["SECRET_KEY"] or not app.config["DATABASE_URL"]:
        raise RuntimeError("Faltan las variables de entorno SECRET_KEY y DATABASE_URL")
    logging.basicConfig(level=logging.INFO)
    if produccion:
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
        instalador.instalar(app.config["DATABASE_URL"], os.environ.get("ADMIN_CORREO"), os.environ.get("ADMIN_CLAVE"))

    app.before_request(seguridad.antes_de_solicitud)
    app.after_request(seguridad.cabeceras)
    app.teardown_request(db.cerrar)
    for modulo in (auth, equipos, diagnostico, admin):
        app.register_blueprint(modulo.bp)

    @app.get("/")
    def inicio():
        return send_from_directory(app.static_folder, "index.html")

    @app.errorhandler(ErrorValidacion)
    def validacion(e):
        return jsonify(error=e.mensaje, campo=e.campo), 422

    @app.errorhandler(HTTPException)
    def http(e):
        return jsonify(error=MENSAJES.get(e.code, "Error en la solicitud.")), e.code

    @app.errorhandler(Exception)
    def inesperado(e):
        app.logger.exception("Error no controlado")
        return jsonify(error="Ocurrió un error inesperado. Inténtalo de nuevo."), 500

    return app


app = crear_app() if os.environ.get("DATABASE_URL") else None
