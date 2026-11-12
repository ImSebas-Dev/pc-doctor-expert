"""Conexión PostgreSQL por solicitud: confirma si la solicitud termina bien y revierte si falla."""
import psycopg
from flask import current_app, g
from psycopg.rows import dict_row


def conexion() -> psycopg.Connection:
    if "db" not in g:
        g.db = psycopg.connect(current_app.config["DATABASE_URL"], connect_timeout=10, row_factory=dict_row, prepare_threshold=None)
    return g.db


def uno(sql: str, params=()):
    return conexion().execute(sql, params).fetchone()


def todos(sql: str, params=()):
    return conexion().execute(sql, params).fetchall()


def cerrar(error=None) -> None:
    cx = g.pop("db", None)
    if cx is not None:
        try:
            cx.rollback() if error else cx.commit()
        finally:
            cx.close()
