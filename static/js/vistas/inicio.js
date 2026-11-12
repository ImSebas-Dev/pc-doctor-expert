/* Panel de inicio: acceso rápido al diagnóstico, equipos y últimos resultados. */
import { api, sesion } from "../api.js";
import { fecha, h, mensaje, porcentaje } from "../ui.js";

export async function inicio() {
  const [{ equipos }, { diagnosticos }] = await Promise.all([api("get", "/api/equipos"), api("get", "/api/diagnosticos")]);
  const nombre = sesion.usuario.nombre.split(" ")[0];
  const ultimos = diagnosticos.slice(0, 3);
  const nodo = h("div", null, h("h1", null, `Hola, ${nombre}`),
    h("p", { class: "subtitulo" }, "¿Tu computador falla? Responde unas preguntas y te mostraremos las causas más probables y qué hacer."),
    equipos.length ? null : mensaje("info", "Para empezar, registra tu equipo."),
    h("div", { class: "acciones" }, equipos.length ? h("a", { class: "boton primario", href: "#/diagnostico" }, "Iniciar un diagnóstico") : h("a", { class: "boton primario", href: "#/equipos" }, "Registrar mi equipo")),
    h("div", { class: "rejilla" },
      h("section", { class: "tarjeta", "aria-labelledby": "t-equipos" }, h("h2", { id: "t-equipos" }, "Mis equipos"),
        h("p", null, equipos.length ? `Tienes ${equipos.length} ${equipos.length === 1 ? "equipo registrado" : "equipos registrados"}.` : "Aún no tienes equipos."),
        h("a", { href: "#/equipos" }, "Administrar equipos")),
      h("section", { class: "tarjeta", "aria-labelledby": "t-ult" }, h("h2", { id: "t-ult" }, "Últimos diagnósticos"),
        ultimos.length ? h("ul", { class: "limpia sin-vinetas" }, ultimos.map((d) => h("li", null, h("a", { href: `#/historial/${d.id}` }, `${d.principal} (${porcentaje(d.peso)})`), h("br"), `${d.equipo} · ${fecha(d.creado_en)}`)))
          : h("p", null, "Todavía no has hecho ningún diagnóstico."),
        diagnosticos.length ? h("a", { href: "#/historial" }, "Ver todo el historial") : null)));
  return { titulo: "Inicio", nodo };
}
