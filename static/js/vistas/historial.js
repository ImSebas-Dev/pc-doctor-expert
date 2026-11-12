/* Historial y detalle con explicación del diagnóstico (RF-03). */
import { api } from "../api.js";
import { campo, fecha, h, icono, mensaje, porcentaje, tabla } from "../ui.js";

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

const ESTADO = { cumple: ["Cumple", "estado-cumple", "exito"], no_cumple: ["No cumple", "estado-no", "error"], sin_dato: ["Sin dato", "estado-sin", "info"] };

function barra(hip) {
  const b = h("span");
  b.style.setProperty("--p", `${hip.peso}%`);
  return h("div", { class: "peso" }, h("span", { class: "nombre" }, hip.nombre), h("span", { class: "valor" }, porcentaje(hip.peso)), h("div", { class: "barra-peso", "aria-hidden": "true" }, b));
}

export async function detalle({ id }) {
  const d = await api("get", `/api/diagnosticos/${encodeURIComponent(id)}`);
  const [principal, ...otras] = d.hipotesis;
  const nombres = Object.fromEntries(d.hipotesis.map((x) => [x.codigo, x.nombre]));
  const nodo = h("article", null, h("h1", null, `Diagnóstico de ${d.diagnostico.equipo}`), h("p", { class: "subtitulo" }, fecha(d.diagnostico.creado_en)),
    d.concluyente ? null : mensaje("advertencia", "El resultado no es concluyente: las respuestas no coinciden lo suficiente con ninguna falla registrada. Te recomendamos la revisión de un técnico."),
    mensaje("info", "Este resultado es orientativo y no reemplaza la revisión de un técnico."),
    h("section", { class: "tarjeta principal", "aria-labelledby": "prin" },
      h("h2", { id: "prin" }, d.concluyente ? "Causa más probable" : "Hipótesis con mayor coincidencia"), barra(principal),
      h("p", null, h("span", { class: "insignia neutra" }, principal.categoria)),
      h("h3", null, "Por qué puede ocurrir"), h("p", null, principal.causa),
      h("h3", null, "Qué puedes hacer"), h("ol", { class: "pasos" }, principal.recomendaciones.map((r) => h("li", null, r)))),
    h("section", { "aria-labelledby": "otras" }, h("h2", { id: "otras" }, "Otras causas posibles"), h("div", { class: "tarjeta" }, otras.map(barra))),
    h("section", { "aria-labelledby": "porque" }, h("h2", { id: "porque" }, "¿Por qué este resultado?"),
      h("p", null, "Estas son las respuestas que usó el sistema y las reglas que consultó."),
      tabla("Evidencias del diagnóstico", ["Pregunta o dato", "Respuesta"], d.evidencias.map((e) => [e.texto + (e.derivada ? " (deducido por el sistema)" : ""), e.respuesta])),
      h("h3", null, "Reglas consultadas"),
      d.reglas.map((r) => h("details", null, h("summary", null, `${r.codigo} · ${nombres[r.hipotesis]} — coincide ${porcentaje(r.coincidencia)}`),
        h("p", null, r.texto),
        tabla(`Condiciones de la regla ${r.codigo}`, ["Condición", "Esperado", "Tu respuesta", "Estado"], r.condiciones.map((c) => {
          const [texto, clase] = ESTADO[c.estado];
          return [c.descripcion, c.esperado, c.respondido ?? "—", h("span", { class: clase }, texto)];
        }))))),
    h("div", { class: "acciones" }, h("a", { class: "boton primario", href: "#/diagnostico" }, "Nuevo diagnóstico"), h("a", { class: "boton", href: "#/historial" }, "Volver al historial")));
  return { titulo: `Diagnóstico de ${d.diagnostico.equipo}`, nodo };
}
