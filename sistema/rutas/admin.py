"""Administración: usuarios, conocimiento y pruebas (RF-01, RF-04). Todas las rutas exigen el rol administrador."""
from flask import Blueprint, abort, g, jsonify

from .. import conocimiento
from ..db import conexion, todos, uno
from ..motor.motor import SesionDiagnostico
from ..seguridad import auditar, requiere_admin
from ..validacion import ErrorValidacion, booleano, cadena, cuerpo, lista

bp = Blueprint("admin", __name__, url_prefix="/api/admin")


@bp.get("/usuarios")
@requiere_admin
def usuarios():
    return jsonify(usuarios=todos("""SELECT u.id, u.nombre, u.correo, r.nombre AS rol, u.activo, u.creado_en
                                     FROM tx.usuario u JOIN tx.rol r ON r.id = u.rol_id ORDER BY u.creado_en"""), yo=g.usuario["id"])


@bp.patch("/usuarios/<int:uid>")
@requiere_admin
def actualizar_usuario(uid):
    d = cuerpo()
    rol, activo = cadena(d, "rol", "Rol", 1, 15), booleano(d, "activo", "Estado")
    if rol not in ("usuario", "administrador"):
        raise ErrorValidacion("Rol no válido.", "rol")
    if uid == g.usuario["id"] and (rol != "administrador" or not activo):
        raise ErrorValidacion("No puedes quitarte el rol de administrador ni desactivar tu propia cuenta.")
    if not uno("UPDATE tx.usuario SET rol_id=(SELECT id FROM tx.rol WHERE nombre=%s), activo=%s WHERE id=%s RETURNING id", (rol, activo, uid)):
        abort(404)
    auditar("admin_usuario_actualizar", "permitido", g.usuario["id"])
    return jsonify(ok=True)


@bp.get("/hipotesis")
@requiere_admin
def hipotesis():
    return jsonify(hipotesis=todos("SELECT codigo, nombre, categoria, confianza, causa_probable, recomendaciones, fuente, validada FROM kb.hipotesis ORDER BY codigo"))


@bp.put("/hipotesis/<codigo>")
@requiere_admin
def editar_hipotesis(codigo):
    d = cuerpo()
    datos = (cadena(d, "nombre", "Nombre", 3, 80), cadena(d, "causa_probable", "Causa probable", 10, 500),
             lista(d, "recomendaciones", "Recomendaciones", 2, 8, 5, 300), booleano(d, "validada", "Validada por el experto"), codigo)
    if not uno("UPDATE kb.hipotesis SET nombre=%s, causa_probable=%s, recomendaciones=%s, validada=%s WHERE codigo=%s RETURNING id", datos):
        abort(404)
    auditar("admin_conocimiento_editar", "permitido", g.usuario["id"])
    conexion().commit()
    conocimiento.recargar()
    return jsonify(ok=True)


@bp.get("/reglas")
@requiere_admin
def reglas():
    return jsonify(reglas=todos("""SELECT r.codigo, r.tipo, r.texto, h.codigo AS hipotesis, r.confianza
                                   FROM kb.regla r LEFT JOIN kb.hipotesis h ON h.id = r.hipotesis_id ORDER BY r.tipo, r.codigo"""))


@bp.get("/pruebas")
@requiere_admin
def ultimas_pruebas():
    return jsonify(pruebas=todos("""SELECT DISTINCT ON (cp.id) cp.nombre AS caso, he.codigo AS esperada, ho.codigo AS obtenida, e.aprobado, e.ejecutado_en
                                    FROM tx.caso_prueba cp JOIN kb.hipotesis he ON he.id = cp.hipotesis_esperada_id
                                    LEFT JOIN tx.ejecucion_prueba e ON e.caso_id = cp.id LEFT JOIN kb.hipotesis ho ON ho.id = e.hipotesis_obtenida_id
                                    ORDER BY cp.id, e.ejecutado_en DESC"""))


@bp.post("/pruebas")
@requiere_admin
def ejecutar_pruebas():
    casos = todos("""SELECT cp.id, cp.nombre, he.codigo AS esperada, f.nombre AS hecho, t.valor FROM tx.caso_prueba cp
                     JOIN kb.hipotesis he ON he.id = cp.hipotesis_esperada_id JOIN tx.caso_prueba_hecho t ON t.caso_id = cp.id
                     JOIN kb.hecho f ON f.id = t.hecho_id ORDER BY cp.id""")
    agrupados: dict = {}
    for c in casos:
        agrupados.setdefault(c["id"], {"nombre": c["nombre"], "esperada": c["esperada"], "hechos": []})["hechos"].append((c["hecho"], c["valor"]))
    for cid, caso in agrupados.items():
        # usuario simulado: confirma los hechos del caso y responde «no» a lo demás
        sesion, real = SesionDiagnostico(conocimiento.repo()), dict(caso["hechos"])
        while (pregunta := sesion.siguiente_pregunta()) is not None:
            h = pregunta.hecho
            sesion.responder(real.get(h.nombre, "falso" if "falso" in h.valores else None))
        diag = sesion.resultado()
        caso["obtenida"] = diag.ranking[0].hipotesis.codigo if diag.concluyente else "P00"
        caso["aprobado"] = caso["obtenida"] == caso["esperada"]
        conexion().execute("INSERT INTO tx.ejecucion_prueba(caso_id,usuario_id,hipotesis_obtenida_id,aprobado) VALUES (%s,%s,(SELECT id FROM kb.hipotesis WHERE codigo=%s),%s)",
                           (cid, g.usuario["id"], caso["obtenida"], caso["aprobado"]))
    return jsonify(pruebas=[{"caso": c["nombre"], "esperada": c["esperada"], "obtenida": c["obtenida"], "aprobado": c["aprobado"]} for c in agrupados.values()])
