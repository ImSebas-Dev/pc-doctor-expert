"""Contrato de acceso a la base de conocimiento (capa de datos)."""
from abc import ABC, abstractmethod
from .entidades import Hipotesis, Hecho, Granulo, ReglaDerivacion


class RepositorioConocimiento(ABC):
    """Cada método es una consulta granular: devuelve solo las piezas de conocimiento que se necesitan."""

    @abstractmethod
    def hipotesis(self) -> list[Hipotesis]: ...

    @abstractmethod
    def hecho(self, nombre: str) -> Hecho | None: ...

    @abstractmethod
    def granulos_por_hecho(self, nombre: str) -> list[Granulo]:
        """Condiciones de reglas de diagnóstico que mencionan el hecho."""

    @abstractmethod
    def reglas_derivacion_por_hecho(self, nombre: str) -> list[ReglaDerivacion]:
        """Reglas RH que usan el hecho (con todas sus condiciones)."""

    @abstractmethod
    def reglas_derivacion_por_conclusion(self, nombre: str) -> list[ReglaDerivacion]:
        """Reglas RH cuya conclusión es el hecho (para inferencia hacia atrás)."""

    @abstractmethod
    def granulos_preguntables(self, hipotesis: list[str], excluidos: set[str]) -> list[tuple[Hecho, Granulo]]:
        """Condiciones, sobre hechos que se pueden preguntar, de las hipótesis candidatas."""
