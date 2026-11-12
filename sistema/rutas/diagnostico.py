"""Diagnóstico guiado, explicación e historial (RF-02, RF-03). El estado vive en el navegador: se rehace con las respuestas dadas."""
from flask import Blueprint, abort, g, jsonify, request

from .. import conocimiento
from ..db import conexion, todos, uno
from ..etiquetas import etiqueta
from ..motor.entidades import Condicion
from ..motor.motor import SesionDiagnostico
from ..motor.parametros import ParametrosInferencia
from ..seguridad import requiere_sesion
from ..validacion import ErrorValidacion, cuerpo, entero

bp = Blueprint("diagnostico", __name__, url_prefix="/api")
PARAMS = ParametrosInferencia()


def _leer():
    d = cuerpo()
    equipo = uno("SELECT id, nombre FROM tx.equipo WHERE id=%s AND usuario_id=%s", (entero(d, "equipo_id", "Equipo", 1, 2**31 - 1), g.usuario["id"]))
    if equipo is None:
        abort(404)
    lista = d.get("respuestas")
    if not isinstance(lista, list) or len(lista) > PARAMS.max_preguntas:
        raise ErrorValidacion("Las respuestas no son válidas.", "respuestas")
    repo, vistos, respuestas = conocimiento.repo(), set(), []
    for x in lista:
        nombre, valor = (x.get("hecho"), x.get("valor")) if isinstance(x, dict) else (None, None)
        hecho = repo.hecho(nombre) if isinstance(nombre, str) else None
        if hecho is None or not hecho.preguntable or nombre in vistos or (valor is not None and valor not in hecho.valores):
            raise ErrorValidacion("Las respuestas no son válidas.", "respuestas")
        vistos.add(nombre)
        respuestas.append((nombre, valor))
    sesion = SesionDiagnostico(conocimiento.repo())
    sesion.reproducir(respuestas)
    return equipo, sesion, sesion.siguiente_pregunta()


def _ranking(diag):
    return [{"codigo": r.hipotesis.codigo, "nombre": r.hipotesis.nombre, "peso": round(r.peso * 100, 1)} for r in diag.ranking]


@bp.post("/diagnosticos/paso")
@requiere_sesion
def paso():
    _, sesion, pregunta = _leer()
    diag = sesion.resultado()
    if pregunta is None:
        return jsonify(terminado=True, concluyente=diag.concluyente, ranking=_ranking(diag))
    return jsonify(terminado=False, numero=sesion.preguntas_hechas + 1, maximo=PARAMS.max_preguntas, ranking=_ranking(diag),
                   pregunta={"hecho": pregunta.hecho.nombre, "texto": pregunta.hecho.pregunta,
                             "opciones": [{"valor": v, "etiqueta": etiqueta(v)} for v in pregunta.hecho.valores]})


def _reglas(filtro: str, params):
    """Reglas de diagnóstico con sus condiciones (una fila por condición)."""
    filas = todos(f"""SELECT r.id, h.codigo AS hipotesis, f.nombre AS hecho, f.descripcion, c.operador, c.valor
                      FROM kb.regla r JOIN kb.hipotesis h ON h.id = r.hipotesis_id JOIN kb.regla_condicion c ON c.regla_id = r.id
                      JOIN kb.hecho f ON f.id = c.hecho_id WHERE r.tipo = 'diagnostico' AND {filtro} ORDER BY r.id, c.orden""", params)
    reglas: dict = {}
    for f in filas:
        reglas.setdefault(f["id"], {"id": f["id"], "hipotesis": f["hipotesis"], "condiciones": []})["condiciones"].append(f)
    return list(reglas.values())


def _evaluar(regla, evidencia):
    """Marca cada condición como cumple, no cumple o sin dato, y calcula el porcentaje de condiciones cumplidas."""
    filas = []
    for c in regla["condiciones"]:
        real = evidencia.get(c["hecho"])
        estado = "sin_dato" if real is None else ("cumple" if Condicion(c["hecho"], c["operador"], c["valor"]).evaluar(real) else "no_cumple")
        filas.append({"descripcion": c["descripcion"], "esperado": etiqueta(c["valor"]), "respondido": etiqueta(real) if real else None, "estado": estado})
    cumplidas = sum(f["estado"] == "cumple" for f in filas)
    return filas, round(100 * cumplidas / len(filas), 2), cumplidas


@bp.post("/diagnosticos")
@requiere_sesion
def guardar():
    equipo, sesion, pregunta = _leer()
    if pregunta is not None:
        raise ErrorValidacion("El diagnóstico aún no ha terminado.", "respuestas")
    diag = sesion.resultado()
    cx = conexion()
    with cx.transaction():
        did = uno("INSERT INTO tx.diagnostico(equipo_id, estado) VALUES (%s, 'finalizado') RETURNING id", (equipo["id"],))["id"]
        with cx.cursor() as cur:
            cur.executemany("INSERT INTO tx.diagnostico_hecho SELECT %s, id, %s FROM kb.hecho WHERE nombre = %s",
                            [(did, valor, hecho) for hecho, valor in diag.evidencia.items()])
            cur.executemany("INSERT INTO tx.diagnostico_hipotesis SELECT %s, id, %s, %s FROM kb.hipotesis WHERE codigo = %s",
                            [(did, round(r.peso * 100, 2), i == 0, r.hipotesis.codigo) for i, r in enumerate(diag.ranking)])
            reglas = _reglas("h.codigo = ANY(%s)", ([r.hipotesis.codigo for r in diag.ranking],))
            cur.executemany("INSERT INTO tx.diagnostico_regla VALUES (%s, %s, %s)",
                            [(did, r["id"], _evaluar(r, diag.evidencia)[1]) for r in reglas])
    return jsonify(id=did), 201


@bp.get("/diagnosticos")
@requiere_sesion
def historial():
    filtro, params = "e.usuario_id = %s", [g.usuario["id"]]
    if (eq := request.args.get("equipo_id", type=int)) is not None:
        filtro, params = filtro + " AND e.id = %s", params + [eq]
    filas = todos(f"""SELECT d.id, d.creado_en, e.id AS equipo_id, e.nombre AS equipo, h.codigo, h.nombre AS principal, dh.coincidencia AS peso
                      FROM tx.diagnostico d JOIN tx.equipo e ON e.id = d.equipo_id
                      JOIN tx.diagnostico_hipotesis dh ON dh.diagnostico_id = d.id AND dh.es_principal JOIN kb.hipotesis h ON h.id = dh.hipotesis_id
                      WHERE {filtro} ORDER BY d.creado_en DESC LIMIT 200""", params)
    return jsonify(diagnosticos=[{**f, "peso": float(f["peso"])} for f in filas])


@bp.get("/diagnosticos/<int:did>")
@requiere_sesion
def detalle(did):
    d = uno("""SELECT d.id, d.creado_en, e.id AS equipo_id, e.nombre AS equipo FROM tx.diagnostico d JOIN tx.equipo e ON e.id = d.equipo_id
               WHERE d.id = %s AND e.usuario_id = %s""", (did, g.usuario["id"]))
    if d is None:
        abort(404)
    hipotesis = todos("""SELECT h.codigo, h.nombre, h.categoria, h.causa_probable AS causa, h.recomendaciones, dh.coincidencia AS peso, dh.es_principal AS principal
                         FROM tx.diagnostico_hipotesis dh JOIN kb.hipotesis h ON h.id = dh.hipotesis_id WHERE dh.diagnostico_id = %s ORDER BY dh.coincidencia DESC, h.codigo""", (did,))
    hipotesis = [{**h, "peso": float(h["peso"])} for h in hipotesis]
    evidencias = todos("""SELECT f.nombre, f.tipo, f.descripcion, f.pregunta, dh.valor FROM tx.diagnostico_hecho dh JOIN kb.hecho f ON f.id = dh.hecho_id
                          WHERE dh.diagnostico_id = %s ORDER BY (f.tipo = 'derivado'), f.nodo, f.nombre""", (did,))
    valores = {e["nombre"]: e["valor"] for e in evidencias}
    reglas = [{"hipotesis": r["hipotesis"], "condiciones": c, "coincidencia": p, "cumplidas": n}
              for r in _reglas("r.id IN (SELECT regla_id FROM tx.diagnostico_regla WHERE diagnostico_id = %s)", (did,))
              for c, p, n in [_evaluar(r, valores)]]
    principal = next(h for h in hipotesis if h["principal"])
    return jsonify(diagnostico=d, concluyente=principal["codigo"] != PARAMS.codigo_cierre and principal["peso"] >= PARAMS.umbral_no_concluyente * 100,
                   hipotesis=hipotesis, reglas=reglas,
                   evidencias=[{"texto": e["pregunta"] or e["descripcion"], "respuesta": etiqueta(e["valor"]), "derivada": e["tipo"] == "derivado"} for e in evidencias])
