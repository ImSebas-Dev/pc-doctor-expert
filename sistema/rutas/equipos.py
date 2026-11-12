"""Equipos del usuario (RF-01). Toda consulta filtra por el dueño: un usuario nunca ve equipos ajenos."""
import psycopg.errors
from flask import Blueprint, abort, g, jsonify

from ..db import conexion, todos, uno
from ..seguridad import requiere_sesion
from ..validacion import ErrorValidacion, cadena, cuerpo, entero

bp = Blueprint("equipos", __name__, url_prefix="/api/equipos")
CAMPOS = "id, nombre, procesador, ram_gb, gpu, almacenamiento, sistema_operativo"


def _leer(d):
    return (cadena(d, "nombre", "Nombre del equipo", 2, 60), cadena(d, "procesador", "Procesador", 2, 80),
            entero(d, "ram_gb", "Memoria RAM (GB)", 1, 1024), cadena(d, "gpu", "Tarjeta gráfica", 2, 80),
            cadena(d, "almacenamiento", "Almacenamiento", 2, 60), cadena(d, "sistema_operativo", "Sistema operativo", 2, 60))


def _guardar(sql, params):
    try:
        with conexion().transaction():
            return uno(sql, params)
    except psycopg.errors.UniqueViolation:
        raise ErrorValidacion("Ya tienes un equipo con ese nombre.", "nombre")


@bp.get("")
@requiere_sesion
def listar():
    return jsonify(equipos=todos(f"SELECT {CAMPOS} FROM tx.equipo WHERE usuario_id=%s ORDER BY nombre", (g.usuario["id"],)))


@bp.post("")
@requiere_sesion
def crear():
    fila = _guardar(f"INSERT INTO tx.equipo(usuario_id,nombre,procesador,ram_gb,gpu,almacenamiento,sistema_operativo) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING {CAMPOS}",
                    (g.usuario["id"], *_leer(cuerpo())))
    return jsonify(equipo=fila), 201


@bp.put("/<int:equipo_id>")
@requiere_sesion
def editar(equipo_id):
    fila = _guardar(f"UPDATE tx.equipo SET nombre=%s, procesador=%s, ram_gb=%s, gpu=%s, almacenamiento=%s, sistema_operativo=%s WHERE id=%s AND usuario_id=%s RETURNING {CAMPOS}",
                    (*_leer(cuerpo()), equipo_id, g.usuario["id"]))
    if not fila:
        abort(404)
    return jsonify(equipo=fila)


@bp.delete("/<int:equipo_id>")
@requiere_sesion
def eliminar(equipo_id):
    if not uno("DELETE FROM tx.equipo WHERE id=%s AND usuario_id=%s RETURNING id", (equipo_id, g.usuario["id"])):
        abort(404)
    return "", 204
