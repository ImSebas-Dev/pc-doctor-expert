"""Validación estricta de la entrada: tipo, longitud, formato y caracteres de control."""
import re
from flask import request

_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ErrorValidacion(Exception):
    def __init__(self, mensaje: str, campo: str | None = None):
        super().__init__(mensaje)
        self.mensaje, self.campo = mensaje, campo


def cuerpo() -> dict:
    d = request.get_json(silent=True)
    if not isinstance(d, dict):
        raise ErrorValidacion("La solicitud no es válida.")
    return d


def cadena(d: dict, campo: str, etiqueta: str, minimo: int = 1, maximo: int = 100, patron=None, recortar: bool = True) -> str:
    v = d.get(campo)
    if not isinstance(v, str):
        raise ErrorValidacion(f"{etiqueta}: este dato es obligatorio.", campo)
    v = v.strip() if recortar else v
    if not minimo <= len(v) <= maximo:
        raise ErrorValidacion(f"{etiqueta}: debe tener entre {minimo} y {maximo} caracteres.", campo)
    if _CONTROL.search(v) or (patron and not patron.match(v)):
        raise ErrorValidacion(f"{etiqueta}: el formato no es válido.", campo)
    return v


def entero(d: dict, campo: str, etiqueta: str, minimo: int, maximo: int) -> int:
    v = d.get(campo)
    if isinstance(v, bool) or not isinstance(v, int) or not minimo <= v <= maximo:
        raise ErrorValidacion(f"{etiqueta}: debe ser un número entero entre {minimo} y {maximo}.", campo)
    return v


def booleano(d: dict, campo: str, etiqueta: str) -> bool:
    if not isinstance(d.get(campo), bool):
        raise ErrorValidacion(f"{etiqueta}: valor no válido.", campo)
    return d[campo]


def lista(d: dict, campo: str, etiqueta: str, minimo: int, maximo: int, largo_min: int, largo_max: int) -> list[str]:
    v = d.get(campo)
    if not isinstance(v, list) or not minimo <= len(v) <= maximo:
        raise ErrorValidacion(f"{etiqueta}: indica entre {minimo} y {maximo} elementos.", campo)
    return [cadena({"x": x}, "x", etiqueta, largo_min, largo_max) for x in v]
