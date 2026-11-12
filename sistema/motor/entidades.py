"""Entidades del dominio (capa de lógica de negocio / modelo)."""
from __future__ import annotations
from dataclasses import dataclass, field

_OPERADORES = {
    "=": lambda a, b: a == b,
    ">": lambda a, b: float(a) > float(b),
    "<": lambda a, b: float(a) < float(b),
    ">=": lambda a, b: float(a) >= float(b),
    "<=": lambda a, b: float(a) <= float(b),
}


@dataclass(frozen=True)
class Hipotesis:
    codigo: str
    nombre: str
    categoria: str
    confianza: str
    causa_probable: str
    recomendaciones: tuple


@dataclass(frozen=True)
class Hecho:
    nombre: str
    tipo: str
    descripcion: str
    valores: tuple
    pregunta: str | None
    nodo: str | None

    @property
    def preguntable(self) -> bool:
        return self.pregunta is not None and len(self.valores) >= 2


@dataclass(frozen=True)
class Condicion:
    hecho: str
    operador: str
    valor: str

    def evaluar(self, real: str) -> bool:
        return _OPERADORES[self.operador](real, self.valor)


@dataclass(frozen=True)
class Granulo:
    """Unidad mínima de conocimiento: una condición de una regla de diagnóstico y la hipótesis que sustenta."""
    hipotesis: str
    regla: str
    confianza: str
    condicion: Condicion


@dataclass(frozen=True)
class ReglaDerivacion:
    codigo: str
    conector: str                 # 'Y' o 'O'
    condiciones: tuple
    conclusion_hecho: str
    conclusion_valor: str


@dataclass
class Evidencia:
    """Hechos conocidos de una sesión: respuestas del usuario, mediciones y hechos derivados."""
    valores: dict = field(default_factory=dict)
    origen: dict = field(default_factory=dict)     # hecho -> 'usuario' | 'derivado'

    def tiene(self, hecho: str) -> bool:
        return hecho in self.valores

    def agregar(self, hecho: str, valor: str, origen: str = "usuario") -> None:
        self.valores[hecho] = valor
        self.origen[hecho] = origen


@dataclass(frozen=True)
class ResultadoHipotesis:
    hipotesis: Hipotesis
    peso: float                   # probabilidad posterior (0 a 1)


@dataclass(frozen=True)
class PreguntaSugerida:
    hecho: Hecho
    ganancia: float               # ganancia de información esperada, en bits


@dataclass(frozen=True)
class Diagnostico:
    ranking: tuple                # ResultadoHipotesis ordenados de mayor a menor peso
    concluyente: bool
    preguntas_hechas: int
    evidencia: dict
