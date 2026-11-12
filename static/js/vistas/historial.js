/* Historial y detalle con explicación del diagnóstico (RF-03). */
import { api } from "../api.js";
import { anillo, campo, fecha, h, icono, mensaje, porcentaje, tabla } from "../ui.js";

export async function historial() {
  const [{ equipos }, { diagnosticos }] = await Promise.all([api("get", "/api/equipos"), api("get", "/api/diagnosticos")]);
  const cuerpo = h("div");
  const filtro = campo({ nombre: "equipo", etiqueta: "Filtrar por equipo", tipo: "select", requerido: false, valor: "", opciones: [{ valor: "", texto: "Todos los equipos" }, ...equipos.map((e) => ({ valor: String(e.id), texto: e.nombre }))] });
  const pintar = () => {
    const sel = filtro.entrada.value;
    const filas = diagnosticos.filter((d) => !sel || String(d.equipo_id) === sel);
    cuerpo.replaceChildren(filas.length ? tabla("Diagnósticos realizados", ["Fecha", "Equipo", "Causa más probable", "Probabilidad", "Detalle"],
      filas.map((d) => [fecha(d.creado_en), d.equipo, d.principal, porcentaje(d.peso), h("a", { href: `#/historial/${d.id}` }, "Ver detalle", h("span", { class: "solo-lector" }, ` del diagnóstico del ${fecha(d.creado_en)}`))]))
      : mensaje("info", diagnosticos.length ? "No hay diagnósticos para ese equipo." : "Aún no has hecho diagnósticos."));
  };
  filtro.entrada.addEventListener("change", pintar);
  pintar();
  return { titulo: "Historial", nodo: h("div", null, h("div", { class: "cabecera-pagina" }, h("h1", null, "Historial de diagnósticos"), h("a", { class: "boton primario", href: "#/diagnostico" }, "Nuevo diagnóstico")), diagnosticos.length ? filtro.raiz : null, cuerpo) };
}

const SENAL = {
  cumple: ["cumple", "senal-cumple", "Coincide"],
  no_cumple: ["no", "senal-no", "No coincide"],
  sin_dato: ["sin", "senal-sin", "No lo sabemos"],
};

function barra(hip) {
  const b = h("span");
  b.style.setProperty("--p", `${hip.peso}%`);
  return h("div", { class: "peso" }, h("span", { class: "nombre" }, hip.nombre), h("span", { class: "valor" }, porcentaje(hip.peso)), h("div", { class: "barra-peso", "aria-hidden": "true" }, b));
}

const nota = (c) => (c.estado === "sin_dato" ? "No tenemos esta información." : c.estado === "cumple" ? `En tu caso: ${c.respondido}.` : `En tu caso: ${c.respondido}. Para esta causa tendría que ser: ${c.esperado}.`);

/* Explicación en lenguaje cotidiano: qué respondió la persona y qué señales coinciden con cada causa. */
function explicacion(d, nombres) {
  const respuestas = d.evidencias.filter((e) => !e.derivada);
  const causas = d.reglas.filter((r) => nombres[r.hipotesis] && r.hipotesis !== "P00");
  return h("section", { "aria-labelledby": "porque" }, h("h2", { id: "porque" }, "¿Cómo llegamos a este resultado?"),
    h("p", null, "Comparamos tus respuestas con las señales típicas de cada falla. Mientras más señales coincidan, más probable es esa causa."),
    h("div", { class: "tarjeta" }, h("h3", null, "Lo que nos respondiste"),
      respuestas.length ? h("ul", { class: "respuestas" }, respuestas.map((e) => h("li", null, h("span", { class: "p" }, e.texto), h("span", { class: "r" }, e.respuesta)))) : h("p", null, "No respondiste ninguna pregunta."),
      causas.length ? h("h3", null, "Señales que revisamos en cada causa") : null,
      causas.map((r, i) => h("details", { open: i === 0 }, h("summary", null, h("span", { class: "resumen-causa" }, h("span", null, nombres[r.hipotesis]), h("span", { class: "insignia neutra" }, `${r.cumplidas} de ${r.condiciones.length}`))),
        h("ul", { class: "senales" }, r.condiciones.map((c) => {
          const [ic, clase, texto] = SENAL[c.estado];
          return h("li", { class: clase }, icono(ic), h("span", { class: "texto" }, c.descripcion, h("span", { class: "nota" }, nota(c))), h("span", { class: "estado" }, texto));
        }))))));
}

export async function detalle({ id }) {
  const d = await api("get", `/api/diagnosticos/${encodeURIComponent(id)}`);
  const [principal, ...otras] = d.hipotesis;
  const nombres = Object.fromEntries(d.hipotesis.map((x) => [x.codigo, x.nombre]));
  const nodo = h("article", null, h("h1", null, `Diagnóstico de ${d.diagnostico.equipo}`), h("p", { class: "subtitulo" }, fecha(d.diagnostico.creado_en)),
    d.concluyente ? null : mensaje("advertencia", "El resultado no es concluyente: tus respuestas no coinciden lo suficiente con ninguna falla conocida. Te recomendamos que lo revise un técnico."),
    h("section", { class: "tarjeta principal", "aria-labelledby": "prin" },
      h("div", { class: "resultado-cabecera" }, anillo(principal.peso, "grande"),
        h("div", { class: "texto" }, h("p", { class: "eyebrow" }, d.concluyente ? "Causa más probable" : "Lo que más se parece"), h("h2", { id: "prin" }, principal.nombre),
          h("span", { class: "insignia neutra" }, principal.categoria), h("span", { class: "solo-lector" }, ` Probabilidad: ${porcentaje(principal.peso)}`))),
      h("h3", null, "Por qué puede ocurrir"), h("p", null, principal.causa),
      h("h3", null, "Qué puedes hacer"), h("ol", { class: "recomendaciones" }, principal.recomendaciones.map((r) => h("li", null, h("span", null, r))))),
    h("section", { "aria-labelledby": "otras" }, h("h2", { id: "otras" }, "Otras causas posibles"), h("div", { class: "tarjeta" }, otras.map(barra))),
    explicacion(d, nombres),
    mensaje("info", "Este resultado es orientativo y no reemplaza la revisión de un técnico."),
    h("div", { class: "acciones" }, h("a", { class: "boton primario", href: "#/diagnostico" }, "Nuevo diagnóstico"), h("a", { class: "boton", href: "#/historial" }, "Volver al historial")));
  return { titulo: `Diagnóstico de ${d.diagnostico.equipo}`, nodo };
}
