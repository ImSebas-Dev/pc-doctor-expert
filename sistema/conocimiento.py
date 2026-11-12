"""Instantánea en memoria de la base de conocimiento (esquema kb). El motor no consulta la BD en cada pregunta."""
import threading

from .db import todos
from .motor.repositorio_memoria import RepositorioMemoria

_cierre, _repo = threading.Lock(), None


def repo() -> RepositorioMemoria:
    global _repo
    with _cierre:
        if _repo is None:
            _repo = _cargar()
        return _repo


def recargar() -> None:
    global _repo
    with _cierre:
        _repo = _cargar()


def _cargar() -> RepositorioMemoria:
    derivacion: dict = {}
    for r in todos("""SELECT r.codigo, r.conector, hc.nombre AS conclusion_hecho, r.valor_conclusion AS conclusion_valor,
                             f.nombre AS hecho, c.operador, c.valor
                      FROM kb.regla r JOIN kb.hecho hc ON hc.id = r.hecho_id JOIN kb.regla_condicion c ON c.regla_id = r.id
                      JOIN kb.hecho f ON f.id = c.hecho_id WHERE r.tipo = 'derivacion' ORDER BY r.codigo, c.orden"""):
        d = derivacion.setdefault(r["codigo"], {"codigo": r["codigo"], "conector": r["conector"], "conclusion_hecho": r["conclusion_hecho"],
                                                "conclusion_valor": r["conclusion_valor"], "condiciones": []})
        d["condiciones"].append({"hecho": r["hecho"], "operador": r["operador"], "valor": r["valor"]})
    return RepositorioMemoria({
        "hipotesis": todos("SELECT codigo, nombre, categoria, confianza, causa_probable, recomendaciones FROM kb.hipotesis ORDER BY codigo"),
        "hechos": todos("SELECT nombre, tipo, descripcion, valores, pregunta, nodo FROM kb.hecho ORDER BY nombre"),
        "granulos": todos("""SELECT h.codigo AS hipotesis, r.codigo AS regla, COALESCE(r.confianza, h.confianza) AS confianza,
                                    f.nombre AS hecho, c.operador, c.valor
                             FROM kb.regla_condicion c JOIN kb.regla r ON r.id = c.regla_id AND r.tipo = 'diagnostico'
                             JOIN kb.hipotesis h ON h.id = r.hipotesis_id JOIN kb.hecho f ON f.id = c.hecho_id ORDER BY r.codigo, c.orden"""),
        "derivacion": list(derivacion.values()),
    })
