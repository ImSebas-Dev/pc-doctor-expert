/* Panel de inicio: acceso rápido al diagnóstico, equipos y últimos resultados. */
import { api, sesion } from "../api.js";
import { anillo, fecha, h, icono, mensaje } from "../ui.js";

const atajo = (href, ic, titulo, detalle) => h("a", { class: "atajo", href }, h("span", { class: "insignia-icono" }, icono(ic)), h("span", null, h("strong", null, titulo), h("span", { class: "detalle" }, detalle)));

export async function inicio() {
  const [{ equipos }, { diagnosticos }] = await Promise.all([api("get", "/api/equipos"), api("get", "/api/diagnosticos")]);
  const nombre = sesion.usuario.nombre.split(" ")[0];
  const ultimos = diagnosticos.slice(0, 3);
  const nodo = h("div", null,
    h("section", { class: "heroe", "aria-labelledby": "saludo" }, h("h1", { id: "saludo" }, `Hola, ${nombre}`),
      h("p", null, "¿Tu computador falla? Responde unas preguntas sencillas y te diremos las causas más probables y qué puedes hacer."),
      h("div", { class: "acciones" }, equipos.length ? h("a", { class: "boton primario", href: "#/diagnostico" }, "Iniciar un diagnóstico") : h("a", { class: "boton primario", href: "#/equipos" }, "Registrar mi equipo"))),
    h("div", { class: "atajos" },
      atajo("#/equipos", "equipos", "Mis equipos", equipos.length ? `${equipos.length} ${equipos.length === 1 ? "registrado" : "registrados"}` : "Agrega el primero"),
      atajo("#/diagnostico", "diagnostico", "Nuevo diagnóstico", "Hasta 10 preguntas"),
      atajo("#/historial", "historial", "Historial", diagnosticos.length ? `${diagnosticos.length} ${diagnosticos.length === 1 ? "diagnóstico" : "diagnósticos"}` : "Aún sin diagnósticos")),
    equipos.length ? null : mensaje("info", "Para empezar, registra tu equipo con sus datos básicos."),
    h("section", { class: "tarjeta", "aria-labelledby": "t-ult" }, h("h2", { id: "t-ult" }, "Últimos diagnósticos"),
      ultimos.length ? h("ul", { class: "lista-resultados" }, ultimos.map((d) => h("li", null, h("a", { href: `#/historial/${d.id}` },
        anillo(d.peso, "pequeno"), h("span", { class: "texto" }, h("span", { class: "titulo-fila" }, d.principal), h("span", { class: "meta" }, `${d.equipo} · ${fecha(d.creado_en)}`))))))
        : h("p", null, "Todavía no has hecho ningún diagnóstico."),
      diagnosticos.length ? h("p", null, h("a", { href: "#/historial" }, "Ver todo el historial")) : null));
  return { titulo: "Inicio", nodo };
}
