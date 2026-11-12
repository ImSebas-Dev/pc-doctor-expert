"""Motor de inferencia: consultas sucesivas y granulares a la base de conocimiento."""
from __future__ import annotations
from .entidades import Evidencia, Diagnostico, ResultadoHipotesis, PreguntaSugerida
from .derivador import Derivador
from .estimador import Estimador
from .selector import SelectorPreguntas
from .repositorio import RepositorioConocimiento
from .parametros import ParametrosInferencia


class SesionDiagnostico:
    """Estado de un diagnóstico en curso. No contiene reglas: todo el conocimiento viene del repositorio."""

    def __init__(self, repo: RepositorioConocimiento, params: ParametrosInferencia | None = None):
        self._repo = repo
        self._p = params or ParametrosInferencia()
        self._hip = {h.codigo: h for h in repo.hipotesis()}
        self.evidencia = Evidencia()
        self.descartados: set[str] = set()          # hechos que el usuario respondió «no sé»
        self.preguntas_hechas = 0
        self._est = Estimador(list(self._hip), self._p)
        self._der = Derivador(repo)
        self._sel = SelectorPreguntas(repo, self._p)
        self._pendiente: PreguntaSugerida | None = None

    # ---- consulta 1: registrar un hecho (respuesta o medición) y propagar ----
    def registrar(self, hecho: str, valor: str) -> None:
        if self.evidencia.tiene(hecho):
            return
        self.evidencia.agregar(hecho, valor, "usuario")
        nuevos = [hecho]
        nuevos += self._der.propagar(self.evidencia, [hecho])
        for h in nuevos:
            self._ponderar(h)

    def _ponderar(self, hecho: str) -> None:
        meta = self._repo.hecho(hecho)
        granulos = self._repo.granulos_por_hecho(hecho)       # consulta 2: gránulos que mencionan el hecho
        if meta and granulos:
            self._est.actualizar(meta, self.evidencia.valores[hecho], granulos)

    def reproducir(self, respuestas: list[tuple[str, str | None]]) -> None:
        """Rehace una sesión desde la lista de respuestas (None = «no sé»); permite una API sin estado."""
        for hecho, valor in respuestas:
            self.preguntas_hechas += 1
            if valor is None:
                self.desconocido(hecho)
            else:
                self.registrar(hecho, valor)

    def desconocido(self, hecho: str) -> None:
        self.descartados.add(hecho)

    # ---- consulta 3: siguiente pregunta ----
    def siguiente_pregunta(self) -> PreguntaSugerida | None:
        if self.terminado():
            return None
        self._pendiente = self._sel.siguiente(self._est, set(self.evidencia.valores), self.descartados)
        return self._pendiente

    def responder(self, valor: str | None) -> None:
        if self._pendiente is None:
            raise RuntimeError("No hay una pregunta pendiente")
        self.preguntas_hechas += 1
        if valor is None:
            self.desconocido(self._pendiente.hecho.nombre)
        else:
            self.registrar(self._pendiente.hecho.nombre, valor)
        self._pendiente = None

    def terminado(self) -> bool:
        r = self._est.ranking()
        if r[0][1] >= self._p.umbral_parada or self.preguntas_hechas >= self._p.max_preguntas:
            return True
        return self._pendiente is None and self._sel.siguiente(self._est, set(self.evidencia.valores), self.descartados) is None

    # ---- resultado ----
    def resultado(self) -> Diagnostico:
        r = self._est.ranking()
        top = tuple(ResultadoHipotesis(self._hip[c], p) for c, p in r[: self._p.cantidad_hipotesis])
        concluyente = r[0][0] != self._p.codigo_cierre and r[0][1] >= self._p.umbral_no_concluyente
        return Diagnostico(top, concluyente, self.preguntas_hechas, dict(self.evidencia.valores))
