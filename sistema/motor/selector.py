"""Selección de la siguiente pregunta por ganancia de información esperada."""
from __future__ import annotations
import math
from .entidades import PreguntaSugerida, Granulo, Hecho
from .estimador import Estimador
from .repositorio import RepositorioConocimiento
from .parametros import ParametrosInferencia


def _h(dist) -> float:
    return -sum(p * math.log2(p) for p in dist if p > 0)


class SelectorPreguntas:
    def __init__(self, repo: RepositorioConocimiento, params: ParametrosInferencia):
        self._repo, self._p = repo, params

    def siguiente(self, est: Estimador, conocidos: set[str], descartados: set[str]) -> PreguntaSugerida | None:
        top = [c for c, _ in est.ranking()[: self._p.candidatas_para_preguntar]]
        # consulta granular: solo condiciones preguntables de las hipótesis candidatas
        filas = self._repo.granulos_preguntables(top, conocidos | descartados)
        por_hecho: dict[str, tuple[Hecho, dict[str, list[Granulo]]]] = {}
        for hecho, g in filas:
            por_hecho.setdefault(hecho.nombre, (hecho, {}))[1].setdefault(g.hipotesis, []).append(g)
        mejor: PreguntaSugerida | None = None
        for hecho, _ in por_hecho.values():
            todos = self._repo.granulos_por_hecho(hecho.nombre)      # consulta granular por candidato
            ganancia = self._ganancia(est, hecho, todos)
            if mejor is None or ganancia > mejor.ganancia:
                mejor = PreguntaSugerida(hecho, ganancia)
        return mejor if mejor and mejor.ganancia >= self._p.ganancia_minima else None

    def _ganancia(self, est: Estimador, hecho: Hecho, todos: list[Granulo]) -> float:
        por_h: dict[str, list[Granulo]] = {}
        for g in todos:
            por_h.setdefault(g.hipotesis, []).append(g)
        antes = _h(est.pesos.values())
        esperada = total = 0.0
        for v in hecho.valores:
            post = [w * est.verosimilitud(hecho, v, por_h.get(c), todos) for c, w in est.pesos.items()]
            pv = sum(post)
            total += pv
            esperada += pv * _h([x / pv for x in post])
        return antes - esperada / total
