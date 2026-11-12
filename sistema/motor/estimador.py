"""Peso probabilístico de las hipótesis (actualización bayesiana por hecho observado)."""
from __future__ import annotations
from .entidades import Granulo, Hecho
from .parametros import ParametrosInferencia


class Estimador:
    """Mantiene P(h | evidencia). Cada hecho nuevo multiplica el peso de cada hipótesis por su verosimilitud."""

    def __init__(self, codigos: list[str], params: ParametrosInferencia):
        self._p = params
        self.pesos = {c: 1.0 / len(codigos) for c in codigos}       # a priori uniforme

    def verosimilitud(self, hecho: Hecho, valor: str, granulos_hipotesis: list[Granulo] | None,
                      todos: list[Granulo]) -> float:
        """P(valor | h). Si h menciona el hecho se usa la confianza de su regla; si no, un valor de coocurrencia."""
        n = len(hecho.valores)
        if n < 2:
            return 0.5
        if granulos_hipotesis:
            c = self._p.fiabilidad[granulos_hipotesis[0].confianza]
            return c if any(g.condicion.evaluar(valor) for g in granulos_hipotesis) else (1 - c) / (n - 1)
        diag = [v for v in hecho.valores if any(g.condicion.evaluar(v) for g in todos)]
        if not diag or len(diag) == n:
            return 1.0 / n
        k = self._p.coocurrencia
        return k / len(diag) if valor in diag else (1 - k) / (n - len(diag))

    def actualizar(self, hecho: Hecho, valor: str, granulos: list[Granulo]) -> None:
        por_h: dict[str, list[Granulo]] = {}
        for g in granulos:
            por_h.setdefault(g.hipotesis, []).append(g)
        for cod in self.pesos:
            self.pesos[cod] *= self.verosimilitud(hecho, valor, por_h.get(cod), granulos)
        self._normalizar()

    def _normalizar(self) -> None:
        s = sum(self.pesos.values())
        piso = 1e-6
        for k in self.pesos:
            self.pesos[k] = max(self.pesos[k] / s, piso)
        s = sum(self.pesos.values())
        for k in self.pesos:
            self.pesos[k] /= s

    def ranking(self) -> list[tuple[str, float]]:
        return sorted(self.pesos.items(), key=lambda kv: -kv[1])
