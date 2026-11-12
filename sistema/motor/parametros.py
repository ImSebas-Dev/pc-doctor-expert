"""Parámetros del motor de inferencia (capa de configuración)."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class ParametrosInferencia:
    # Probabilidad de que el usuario confirme una condición cuando la hipótesis es verdadera,
    # según la confianza que el experto asignó a la regla (kb.regla.confianza).
    fiabilidad: dict = field(default_factory=lambda: {"alta": 0.95, "media": 0.85, "baja": 0.70, "n/a": 0.90})
    cantidad_hipotesis: int = 5          # hipótesis que se muestran con su peso
    umbral_parada: float = 0.80          # se deja de preguntar cuando la primera hipótesis alcanza este peso
    max_preguntas: int = 10               # tope de preguntas por diagnóstico
    ganancia_minima: float = 0.05        # bits mínimos para que una pregunta valga la pena
    umbral_no_concluyente: float = 0.30  # si la primera hipótesis no llega a este peso, el resultado es no concluyente
    coocurrencia: float = 0.35           # prob. de ver el valor «diagnóstico» de un hecho cuando la hipótesis no lo menciona
    candidatas_para_preguntar: int = 12  # hipótesis con más peso que se consideran al elegir la pregunta
    codigo_cierre: str = "P00"           # hipótesis de cierre (diagnóstico no concluyente)
