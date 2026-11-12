"""Repositorio en memoria cargado desde una instantánea de la base de conocimiento (lectura única; el motor no consulta la BD en cada pregunta)."""
from .repositorio import RepositorioConocimiento
from .entidades import Hipotesis, Hecho, Condicion, Granulo, ReglaDerivacion


class RepositorioMemoria(RepositorioConocimiento):
    def __init__(self, d: dict):
        self._h = [Hipotesis(h["codigo"], h["nombre"], h["categoria"], h["confianza"], h["causa_probable"], tuple(h["recomendaciones"])) for h in d["hipotesis"]]
        self._hechos = {x["nombre"]: Hecho(x["nombre"], x["tipo"], x["descripcion"], tuple(x["valores"] or ()), x["pregunta"], x["nodo"]) for x in d["hechos"]}
        self._gr = [Granulo(g["hipotesis"], g["regla"], g["confianza"], Condicion(g["hecho"], g["operador"], g["valor"])) for g in d["granulos"]]
        self._rh = [ReglaDerivacion(r["codigo"], r["conector"], tuple(Condicion(c["hecho"], c["operador"], c["valor"]) for c in r["condiciones"]), r["conclusion_hecho"], r["conclusion_valor"]) for r in d["derivacion"]]

    def hipotesis(self):
        return list(self._h)

    def hecho(self, nombre):
        return self._hechos.get(nombre)

    def granulos_por_hecho(self, nombre):
        return [g for g in self._gr if g.condicion.hecho == nombre]

    def reglas_derivacion_por_hecho(self, nombre):
        return [r for r in self._rh if any(c.hecho == nombre for c in r.condiciones)]

    def reglas_derivacion_por_conclusion(self, nombre):
        return [r for r in self._rh if r.conclusion_hecho == nombre]

    def granulos_preguntables(self, hipotesis, excluidos):
        out = []
        for g in self._gr:
            h = self._hechos[g.condicion.hecho]
            if g.hipotesis in hipotesis and h.preguntable and h.nombre not in excluidos:
                out.append((h, g))
        return out
