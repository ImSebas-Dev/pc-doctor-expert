/* Diagnóstico guiado (RF-02): una pregunta por pantalla, con «No sé» y «Atrás». El estado vive en el navegador. */
import { api } from "../api.js";
import { anunciar, avisar, campo, cargando, formulario, h, mensaje, porcentaje } from "../ui.js";

export async function diagnostico(params) {
  const { equipos } = await api("get", "/api/equipos");
  const nodo = h("div");
  if (!equipos.length) {
    nodo.append(h("h1", null, "Nuevo diagnóstico"), mensaje("info", "Primero registra tu equipo para poder diagnosticarlo."), h("a", { class: "boton primario", href: "#/equipos" }, "Registrar mi equipo"));
    return { titulo: "Nuevo diagnóstico", nodo };
  }
  const elegido = equipos.find((e) => String(e.id) === params.equipo);
  if (elegido) iniciar(nodo, elegido, []);
  else {
    const sel = campo({ nombre: "equipo", etiqueta: "¿Qué equipo quieres diagnosticar?", tipo: "select", valor: String(equipos[0].id), opciones: equipos.map((e) => ({ valor: String(e.id), texto: e.nombre })) });
    nodo.append(h("h1", null, "Nuevo diagnóstico"), h("p", { class: "subtitulo" }, "Te haremos unas pocas preguntas (máximo 10). Responde lo que sepas; si no estás seguro, elige «No sé»."),
      h("section", { class: "tarjeta" }, formulario({ campos: [sel], boton: "Comenzar", enviar: async (d) => iniciar(nodo, equipos.find((e) => String(e.id) === d.equipo), []) })));
  }
  return { titulo: "Nuevo diagnóstico", nodo };
}

async function iniciar(nodo, equipo, respuestas) {
  nodo.replaceChildren(h("h1", null, `Diagnóstico de ${equipo.nombre}`), cargando("Preparando la siguiente pregunta…"));
  let p;
  try { p = await api("post", "/api/diagnosticos/paso", { equipo_id: equipo.id, respuestas }); }
  catch (e) { nodo.replaceChildren(h("h1", null, `Diagnóstico de ${equipo.nombre}`), mensaje("error", e.message), h("button", { class: "boton", type: "button", onclick: () => iniciar(nodo, equipo, respuestas) }, "Reintentar")); return; }
  if (p.terminado) return guardar(nodo, equipo, respuestas);
  const responder = (valor) => iniciar(nodo, equipo, [...respuestas, { hecho: p.pregunta.hecho, valor }]);
  const titulo = h("h2", { id: "pregunta", tabindex: "-1" }, p.pregunta.texto);
  nodo.replaceChildren(h("h1", null, `Diagnóstico de ${equipo.nombre}`),
    h("section", { class: "tarjeta", "aria-labelledby": "pregunta" },
      h("p", { class: "paso-numero" }, `Pregunta ${p.numero} de máximo ${p.maximo}`),
      h("progress", { max: p.maximo, value: p.numero - 1, "aria-label": "Progreso del diagnóstico" }), titulo,
      h("div", { class: "opciones", role: "group", "aria-labelledby": "pregunta" },
        p.pregunta.opciones.map((o) => h("button", { type: "button", class: "boton opcion", onclick: () => responder(o.valor) }, o.etiqueta)),
        h("button", { type: "button", class: "boton opcion", onclick: () => responder(null) }, "No sé")),
      h("div", { class: "acciones" }, respuestas.length ? h("button", { type: "button", class: "boton", onclick: () => iniciar(nodo, equipo, respuestas.slice(0, -1)) }, "Volver a la pregunta anterior") : null,
        h("a", { class: "boton sutil", href: "#/" }, "Cancelar diagnóstico"))),
    h("details", null, h("summary", null, "Causas más probables hasta ahora"),
      h("ul", { class: "limpia sin-vinetas" }, p.ranking.slice(0, 3).map((r) => h("li", null, `${r.nombre}: ${porcentaje(r.peso)}`))),
      h("p", { class: "ayuda" }, "Este ranking se actualiza con cada respuesta.")));
  titulo.focus();
  anunciar(`Pregunta ${p.numero}: ${p.pregunta.texto}`);
}

async function guardar(nodo, equipo, respuestas) {
  nodo.replaceChildren(h("h1", null, `Diagnóstico de ${equipo.nombre}`), cargando("Guardando tu diagnóstico…"));
  try {
    const { id } = await api("post", "/api/diagnosticos", { equipo_id: equipo.id, respuestas });
    avisar("exito", "Diagnóstico terminado y guardado en tu historial.");
    location.hash = `#/historial/${id}`;
  } catch (e) {
    nodo.replaceChildren(h("h1", null, `Diagnóstico de ${equipo.nombre}`), mensaje("error", e.message), h("button", { class: "boton primario", type: "button", onclick: () => guardar(nodo, equipo, respuestas) }, "Reintentar guardado"));
  }
}
