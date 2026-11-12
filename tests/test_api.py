"""Pruebas de la API contra una base PostgreSQL real (DATABASE_URL, ADMIN_CORREO y ADMIN_CLAVE ya instalados)."""
import os
import time
import unittest
import uuid

from app import crear_app
from sistema import seguridad

ADMIN = (os.environ["ADMIN_CORREO"], os.environ["ADMIN_CLAVE"])
CLAVE = "Clave-Segura-2026"
U01 = {"sintoma_principal": "apagado_reinicio", "temperatura_elevada": "verdadero", "ventilador_anormal": "falso",
       "calor_cpu": "verdadero", "calor_gpu": "falso", "calor_flujo": "falso"}
EQUIPO = {"nombre": "Portátil", "procesador": "Intel Core i7", "ram_gb": 16, "gpu": "NVIDIA GTX 1660", "almacenamiento": "SSD 512 GB", "sistema_operativo": "Windows 11"}


class Cliente:
    def __init__(self, app):
        self.c, self.csrf = app.test_client(), None
        self.csrf = self.c.get("/api/sesion").get_json()["csrf"]

    def pedir(self, metodo, ruta, datos=None, csrf=True):
        cab = {"X-CSRF-Token": self.csrf} if csrf else {}
        r = getattr(self.c, metodo)(ruta, json=datos, headers=cab) if datos is not None or metodo != "get" else self.c.get(ruta)
        if r.is_json and isinstance(r.get_json(), dict) and "csrf" in r.get_json():
            self.csrf = r.get_json()["csrf"]
        return r


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = crear_app({"TESTING": True})

    def setUp(self):
        for lim in (seguridad.fallos_por_ip, seguridad.fallos_por_correo, seguridad.registros_por_ip):
            lim._h.clear()

    def usuario_nuevo(self):
        cl = Cliente(self.app)
        r = cl.pedir("post", "/api/registro", {"nombre": "Ana Prueba", "correo": f"{uuid.uuid4().hex[:10]}@prueba.test", "clave": CLAVE})
        self.assertEqual(r.status_code, 201, r.get_json())
        return cl

    def admin(self):
        cl = Cliente(self.app)
        r = cl.pedir("post", "/api/login", {"correo": ADMIN[0], "clave": ADMIN[1]})
        self.assertEqual(r.status_code, 200, r.get_json())
        return cl


class Seguridad(Base):
    def test_cabeceras(self):
        r = self.app.test_client().get("/")
        csp = r.headers["Content-Security-Policy"]
        self.assertIn("script-src 'self'", csp)
        self.assertNotIn("unsafe-inline", csp)
        self.assertEqual(r.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(self.app.test_client().get("/api/sesion").headers["Cache-Control"], "no-store")

    def test_sin_sesion_401_y_csrf_403(self):
        cl = Cliente(self.app)
        self.assertEqual(cl.pedir("get", "/api/equipos").status_code, 401)
        self.assertEqual(cl.pedir("post", "/api/login", {"correo": "a@b.co", "clave": "x"}, csrf=False).status_code, 403)
        self.assertEqual(cl.c.post("/api/login", data="x", headers={"X-CSRF-Token": cl.csrf}).status_code, 415)

    def test_login_generico_y_limite(self):
        cl = Cliente(self.app)
        a = cl.pedir("post", "/api/login", {"correo": ADMIN[0], "clave": "mala-clave-1"})
        b = cl.pedir("post", "/api/login", {"correo": "noexiste@prueba.test", "clave": "mala-clave-1"})
        self.assertEqual((a.status_code, b.status_code), (401, 401))
        self.assertEqual(a.get_json(), b.get_json())
        for _ in range(4):
            cl.pedir("post", "/api/login", {"correo": ADMIN[0], "clave": "mala-clave-1"})
        self.assertEqual(cl.pedir("post", "/api/login", {"correo": ADMIN[0], "clave": ADMIN[1]}).status_code, 429)

    def test_inyeccion_sql_no_rompe(self):
        r = Cliente(self.app).pedir("post", "/api/login", {"correo": "' OR 1=1 --", "clave": "x' OR '1'='1"})
        self.assertEqual(r.status_code, 401)

    def test_politica_de_clave_y_duplicados(self):
        cl = Cliente(self.app)
        base = {"nombre": "Ana", "correo": f"{uuid.uuid4().hex[:8]}@prueba.test"}
        self.assertEqual(cl.pedir("post", "/api/registro", {**base, "clave": "corta"}).status_code, 422)
        self.assertEqual(cl.pedir("post", "/api/registro", {**base, "clave": "1234567890"}).status_code, 422)
        self.assertEqual(cl.pedir("post", "/api/registro", {**base, "clave": CLAVE}).status_code, 201)
        self.assertEqual(Cliente(self.app).pedir("post", "/api/registro", {**base, "clave": CLAVE}).status_code, 422)

    def test_sesion_expira_por_inactividad(self):
        cl = self.usuario_nuevo()
        self.assertEqual(cl.pedir("get", "/api/equipos").status_code, 200)
        with cl.c.session_transaction() as s:
            s["ult"] = int(time.time()) - seguridad.INACTIVIDAD - 5
        self.assertEqual(cl.pedir("get", "/api/equipos").status_code, 401)

    def test_cuerpo_demasiado_grande(self):
        cl = Cliente(self.app)
        self.assertEqual(cl.pedir("post", "/api/login", {"correo": "a" * 40000, "clave": "x"}).status_code, 413)


class ControlDeAcceso(Base):
    def test_un_usuario_no_ve_lo_de_otro(self):
        a, b = self.usuario_nuevo(), self.usuario_nuevo()
        eq = a.pedir("post", "/api/equipos", EQUIPO).get_json()["equipo"]
        self.assertEqual(b.pedir("get", "/api/equipos").get_json()["equipos"], [])
        self.assertEqual(b.pedir("put", f"/api/equipos/{eq['id']}", EQUIPO).status_code, 404)
        self.assertEqual(b.pedir("delete", f"/api/equipos/{eq['id']}", {}).status_code, 404)
        self.assertEqual(b.pedir("post", "/api/diagnosticos/paso", {"equipo_id": eq["id"], "respuestas": []}).status_code, 404)
        did = self.diagnosticar(a, eq["id"])
        self.assertEqual(b.pedir("get", f"/api/diagnosticos/{did}").status_code, 404)

    def test_rutas_admin_solo_para_admin(self):
        u = self.usuario_nuevo()
        for ruta in ("usuarios", "hipotesis", "reglas", "pruebas"):
            self.assertEqual(u.pedir("get", f"/api/admin/{ruta}").status_code, 403, ruta)
        self.assertEqual(u.pedir("post", "/api/admin/pruebas", {}).status_code, 403)

    def diagnosticar(self, cl, equipo_id):
        respuestas = []
        for _ in range(12):
            p = cl.pedir("post", "/api/diagnosticos/paso", {"equipo_id": equipo_id, "respuestas": respuestas}).get_json()
            if p["terminado"]:
                break
            h = p["pregunta"]["hecho"]
            respuestas.append({"hecho": h, "valor": U01.get(h)})
        self.assertTrue(p["terminado"])
        self.assertEqual(p["ranking"][0]["codigo"], "P01")
        r = cl.pedir("post", "/api/diagnosticos", {"equipo_id": equipo_id, "respuestas": respuestas})
        self.assertEqual(r.status_code, 201)
        return r.get_json()["id"]


class Funcionalidad(Base):
    def test_equipos_crud_y_validacion(self):
        u = self.usuario_nuevo()
        self.assertEqual(u.pedir("post", "/api/equipos", {**EQUIPO, "ram_gb": 0}).status_code, 422)
        self.assertEqual(u.pedir("post", "/api/equipos", {**EQUIPO, "ram_gb": True}).status_code, 422)
        eq = u.pedir("post", "/api/equipos", EQUIPO).get_json()["equipo"]
        self.assertEqual(u.pedir("post", "/api/equipos", EQUIPO).status_code, 422)
        self.assertEqual(u.pedir("put", f"/api/equipos/{eq['id']}", {**EQUIPO, "ram_gb": 32}).get_json()["equipo"]["ram_gb"], 32)
        self.assertEqual(u.pedir("delete", f"/api/equipos/{eq['id']}", {}).status_code, 204)

    def test_diagnostico_completo_con_explicacion(self):
        u = self.usuario_nuevo()
        eq = u.pedir("post", "/api/equipos", EQUIPO).get_json()["equipo"]
        did = ControlDeAcceso.diagnosticar(self, u, eq["id"])
        d = u.pedir("get", f"/api/diagnosticos/{did}").get_json()
        self.assertTrue(d["concluyente"])
        self.assertEqual(len(d["hipotesis"]), 5)
        self.assertEqual(d["hipotesis"][0]["codigo"], "P01")
        self.assertGreaterEqual(len(d["hipotesis"][0]["recomendaciones"]), 2)
        self.assertTrue(d["evidencias"])
        self.assertTrue(any(r["codigo"] == "R-P01" and r["coincidencia"] == 100 for r in d["reglas"]))
        self.assertEqual(u.pedir("get", "/api/diagnosticos").get_json()["diagnosticos"][0]["codigo"], "P01")

    def test_respuestas_manipuladas_se_rechazan(self):
        u = self.usuario_nuevo()
        eq = u.pedir("post", "/api/equipos", EQUIPO).get_json()["equipo"]
        for malas in ([{"hecho": "sintoma_principal", "valor": "<script>"}], [{"hecho": "no_existe", "valor": "x"}],
                      [{"hecho": "sintoma_principal", "valor": "lentitud"}] * 2, [{"hecho": "archivos_corruptos", "valor": "falso"}], "texto", [None]):
            self.assertEqual(u.pedir("post", "/api/diagnosticos/paso", {"equipo_id": eq["id"], "respuestas": malas}).status_code, 422, malas)
        self.assertEqual(u.pedir("post", "/api/diagnosticos", {"equipo_id": eq["id"], "respuestas": []}).status_code, 422)

    def test_perfil_cambio_de_clave(self):
        u = self.usuario_nuevo()
        self.assertEqual(u.pedir("put", "/api/perfil", {"nombre": "Ana", "clave_actual": "otra-clave-xx", "clave_nueva": "Nueva-Clave-2026"}).status_code, 422)
        self.assertEqual(u.pedir("put", "/api/perfil", {"nombre": "Ana B", "clave_actual": CLAVE, "clave_nueva": "Nueva-Clave-2026"}).status_code, 200)

    def test_admin_pruebas_y_conocimiento(self):
        a = self.admin()
        r = a.pedir("post", "/api/admin/pruebas", {}).get_json()["pruebas"]
        self.assertEqual(len(r), 26)
        fallidas = [x for x in r if not x["aprobado"]]
        self.assertEqual(fallidas, [])
        h = next(x for x in a.pedir("get", "/api/admin/hipotesis").get_json()["hipotesis"] if x["codigo"] == "P01")
        ok = a.pedir("put", "/api/admin/hipotesis/P01", {"nombre": h["nombre"], "causa_probable": h["causa_probable"], "recomendaciones": h["recomendaciones"], "validada": True})
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(a.pedir("put", "/api/admin/hipotesis/P01", {"nombre": "x", "causa_probable": "corta", "recomendaciones": ["uno"], "validada": True}).status_code, 422)

    def test_admin_no_puede_autodegradarse(self):
        a = self.admin()
        yo = a.pedir("get", "/api/admin/usuarios").get_json()["yo"]
        self.assertEqual(a.pedir("patch", f"/api/admin/usuarios/{yo}", {"rol": "usuario", "activo": True}).status_code, 422)
        self.usuario_nuevo()
        uid = next(x["id"] for x in a.pedir("get", "/api/admin/usuarios").get_json()["usuarios"] if x["id"] != yo)
        self.assertEqual(a.pedir("patch", f"/api/admin/usuarios/{uid}", {"rol": "usuario", "activo": False}).status_code, 200)
        self.assertEqual(a.pedir("patch", f"/api/admin/usuarios/{uid}", {"rol": "usuario", "activo": True}).status_code, 200)


if __name__ == "__main__":
    unittest.main()
