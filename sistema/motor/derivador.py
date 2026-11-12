"""Derivación de hechos por encadenamiento hacia adelante con lógica trivaluada (verdadero / falso / desconocido)."""
from __future__ import annotations
from .entidades import Evidencia, ReglaDerivacion, Condicion
from .repositorio import RepositorioConocimiento


class Derivador:
    def __init__(self, repo: RepositorioConocimiento):
        self._repo = repo

    @staticmethod
    def _evaluar(c: Condicion, ev: Evidencia):
        if not ev.tiene(c.hecho):
            return None
        return c.evaluar(ev.valores[c.hecho])

    def _resolver(self, r: ReglaDerivacion, ev: Evidencia):
        vals = [self._evaluar(c, ev) for c in r.condiciones]
        if r.conector == "Y":
            if any(v is False for v in vals): return False
            return True if all(v is True for v in vals) else None
        if any(v is True for v in vals): return True
        return False if all(v is False for v in vals) else None

    @staticmethod
    def _complemento(destino, valor):
        """Si la regla no se cumple y el hecho solo tiene dos valores, se concluye el otro valor."""
        if destino and len(destino.valores) == 2 and valor in destino.valores:
            return next(v for v in destino.valores if v != valor)
        return None

    def propagar(self, ev: Evidencia, nuevos: list[str]) -> list[str]:
        """Consulta, por cada hecho nuevo, solo las reglas RH que lo mencionan; devuelve los hechos derivados."""
        derivados, cola, vistas = [], list(nuevos), set()
        while cola:
            hecho = cola.pop()
            derivados += self._hacia_atras(ev, hecho, cola)
            for r in self._repo.reglas_derivacion_por_hecho(hecho):
                if r.codigo in vistas and ev.tiene(r.conclusion_hecho):
                    continue
                res = self._resolver(r, ev)
                if res is None or ev.tiene(r.conclusion_hecho):
                    continue
                destino = self._repo.hecho(r.conclusion_hecho)
                valor = r.conclusion_valor if res else self._complemento(destino, r.conclusion_valor)
                if valor is None:
                    continue
                vistas.add(r.codigo)
                ev.agregar(r.conclusion_hecho, valor, "derivado")
                derivados.append(r.conclusion_hecho)
                cola.append(r.conclusion_hecho)
        return derivados

    def _hacia_atras(self, ev: Evidencia, hecho: str, cola: list[str]) -> list[str]:
        """Si se observa la conclusión de una regla Y, sus condiciones de igualdad también son ciertas."""
        nuevos = []
        for r in self._repo.reglas_derivacion_por_conclusion(hecho):
            if r.conector != "Y" or r.conclusion_valor != ev.valores[hecho]:
                continue
            for c in r.condiciones:
                if c.operador == "=" and not ev.tiene(c.hecho):
                    ev.agregar(c.hecho, c.valor, "derivado")
                    nuevos.append(c.hecho)
                    cola.append(c.hecho)
        return nuevos
